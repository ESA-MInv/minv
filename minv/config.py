import sys
from os.path import join, getmtime, splitext
from ConfigParser import NoOptionError, NoSectionError, RawConfigParser
from datetime import datetime
import shutil

from django.conf import settings
from django.utils.datastructures import SortedDict


class ConfigurationErrors(Exception):
    pass


def section(name):
    """ Helper to set the section of a :class:`Reader`.
    """
    frame = sys._getframe(1)
    locals_ = frame.f_locals

    # Some sanity checks
    assert locals_ is not frame.f_globals and '__module__' in locals_, \
        'implements() can only be used in a class definition'

    locals_["section"] = name


class Option(property):
    """ The :class:`Option` is used as a :class:`property` for :class:`Reader`
        subclasses.

        :param key: the lookup key; defaults to the property name of the
                    :class:`Reader`.
        :param type: the type to parse the raw value; by default the raw
                     string is returned
        :param separator: the separator for list options; by default no list
                          is assumed
        :param required: if ``True`` raise an error if the option does not
                         exist
        :param default: the default value
        :param section: override the section for this option
    """

    def __init__(self, key=None, type=None, separator=None, required=False,
                 default=None, section=None, doc=None):

        super(Option, self).__init__(self.fget, self.fset, self.fdel)

        self.key = key  # needs to be set by the reader metaclass
        self.type = type
        self.separator = separator
        self.required = required
        self.default = default
        self.section = section or sys._getframe(1).f_locals.get("section")

    def fget(self, reader):
        section = self.section or reader.section
        try:
            if self.type is bool:
                raw_value = reader._config.getboolean(section, self.key)
            else:
                raw_value = reader._config.get(section, self.key)
        except (NoOptionError, NoSectionError):
            if not self.required:
                return self.default
            raise

        if self.separator is not None:
            if raw_value is None:
                return []
            return map(self.type, raw_value.split(self.separator))

        elif self.type:
            return self.type(raw_value)

        else:
            return raw_value

    def fset(self, reader, value):
        if self.separator:
            value = self.separator.join(value)
        elif self.type is bool:
            value = str(value).lower()

        if not reader._config.has_section(self.section):
            reader._config.add_section(self.section)

        if value is not None:
            reader._config.set(self.section, self.key, value)
        else:
            reader._config.remove_option(self.section, self.key)

    def fdel(self, reader):
        if reader._config.has_section(self.section):
            reader._config.remove_option(self.section, self.key)

    def __repr__(self):
        return "<%s.%s '%s.%s'>" % (
            self.__module__, self.__class__.__name__, self.section, self.key
        )


class SectionOption(property):
    """
    """

    def __init__(self, section=None, doc=None):
        super(SectionOption, self).__init__(self.fget, self.fset, self.fdel)
        self.section = section  # needs to be set by the reader metaclass

    def fget(self, reader):
        return reader.get_section_dict(self.section)

    def fset(self, reader, values):
        reader.set_section_dict(self.section, values)

    def fdel(self, reader):
        reader._config.remove_section(self.section)

    def __repr__(self):
        return "<%s.%s '%s'>" % (
            self.__module__, self.__class__.__name__, self.section
        )


class ReaderMetaclass(type):
    """
    MetaClass for readers. handles the setting of the key for the options and
    the registration within the Reader
    """

    def __new__(cls, name, bases, dct):
        dct["_options"] = []
        return type.__new__(cls, name, bases, dct)

    def __init__(cls, name, bases, dct):
        for key, value in dct.items():
            if isinstance(value, Option):
                if value.key is None:
                    value.key = key
                    value.__doc__ = "%s.%s" % (value.section, value.key)
            elif isinstance(value, SectionOption):
                if value.section is None:
                    value.section = key
                    value.__doc__ = "%s" % (value.section)

            dct["_options"].append(value)

        super(ReaderMetaclass, cls).__init__(name, bases, dct)


class Reader(object):
    """ Configuration Reader.
    """
    __metaclass__ = ReaderMetaclass

    section = None

    def __init__(self, config_path=None):
        # by default, read from the global config dir
        if config_path is None:
            config_path = join(settings.MINV_CONFIG_DIR, "minv.conf")

        self._config_path = config_path
        self._config = None
        self.read()

    def check_config(self):
        errors = []
        for option in self._options:
            try:
                option.fget(self)
            except Exception as exc:
                errors.append(exc)

        if errors:
            raise ConfigurationErrors(errors)

    def write(self, config_path=None):
        self._config.write(open(config_path or self._config_path, "w"))

    def read(self, reset=True):
        if reset or not self._config:
            self._config = RawConfigParser()

        with open(self._config_path) as f:
            self._config.readfp(f)

    def get_section_dict(self, section):
        try:
            return dict(self._config.items(section))
        except NoSectionError:
            return {}

    def set_section_dict(self, section, values):
        self._config.remove_section(section)

        if values:
            self._config.add_section(section)
            for key, value in values.items():
                self._config.set(section, key, value)

    @classmethod
    def from_fileobject(cls, fobj):
        reader = cls()
        reader._config = RawConfigParser()
        reader._config.readfp(fobj)
        return reader


def try_or_none(type_):
    def wrapper(value):
        try:
            return type_(value)
        except:
            return None
    return wrapper


class GlobalReader(Reader):
    section = "minv"
    log_level = Option(default="INFO")

    section = "database"
    host = Option(default="")
    port = Option(type=int, default=5432)
    database = Option(default="minv")
    user = Option(default="minv")
    password = Option(required=True)

    section = "daemon"
    socket_filename = Option(default=None)
    daemon_port = Option(type=try_or_none(int), default=None)
    num_workers = Option(type=int, default=8)


def check_global_configuration(reader):
    keys = (
        "host", "port", "database", "user", "password",
        "socket_filename", "daemon_port", "num_workers"
    )
    errors = []
    for key in keys:
        try:
            getattr(reader, key)
        except Exception as exc:
            errors.append("%s: %s" % (key, exc))

    levels = ("DEBUG", "INFO", "WARN", "ERROR")
    if reader.log_level not in levels:
        errors.append(
            "minv.log_level: invalid value '%s' must be one of %s"
            % (reader.log_level, ", ".join(levels))
        )

    return errors


def global_configuration_changes(old, new):
    changes = SortedDict()
    database_keys = ("host", "port", "database", "user", "password")
    daemon_keys = ("socket_filename", "daemon_port", "num_workers")

    if old.log_level != new.log_level:
        changes["minv.log_level"] = (old.log_level, new.log_level)

    for key in database_keys:
        if getattr(old, key) != getattr(new, key):
            changes["database.%s" % key] = (getattr(old, key), getattr(new, key))

    for key in daemon_keys:
        if getattr(old, key) != getattr(new, key):
            changes["daemon.%s" % key] = (getattr(old, key), getattr(new, key))

    return changes


def backup_config(path):
    """ Move a configuration file to a new path with a timestamp (of its last
    modification) added.
    """
    root, ext = splitext(path)
    timestamp = datetime.fromtimestamp(getmtime(path)).replace(
        microsecond=0, tzinfo=None
    )
    timestr = timestamp.isoformat("T").replace(":", "")
    backup_path = "%s-%s%s" % (
        root, timestr, ext
    )
    shutil.move(path, backup_path)
    return backup_path
