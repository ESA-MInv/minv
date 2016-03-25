import sys
from os.path import join
from ConfigParser import NoOptionError, NoSectionError, RawConfigParser

from django.conf import settings


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
        try:
            return dict(reader._config.items(self.section))
        except NoSectionError:
            return {}

    def fset(self, reader, values):
        reader._config.remove_section(self.section)

        if values:
            reader._config.add_section(self.section)
            for key, value in values.items():
                reader._config.set(self.section, key, value)

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


def try_or_none(type_):
    def wrapper(value):
        try:
            return type_(value)
        except:
            return None
    return wrapper


class DatabaseReader(Reader):
    section("database")
    host = Option(default="")
    port = Option(type=int, default=5432)
    database = Option(default="minv")
    user = Option(default="minv")
    password = Option(required=True)


class DaemonReader(Reader):
    section("daemon")
    socket_filename = Option(default=None)
    port = Option(type=try_or_none(int), default=None)
    num_workers = Option(type=int, default=8)
