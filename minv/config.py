import sys
from ConfigParser import NoOptionError, NoSectionError, RawConfigParser


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

        super(Option, self).__init__(self.fget)

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

    def check(self, reader):
        # TODO: perform checking of config
        #  - required option?
        #  - can parse type?
        errors

    def __repr__(self):
        return "<%s.%s '%s.%s'>" % (
            self.__module__, self.__class__.__name__, self.section, self.key
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

                dct["_options"].append(value)

        super(ReaderMetaclass, cls).__init__(name, bases, dct)


class Reader(object):
    """ Configuration Reader.
    """
    __metaclass__ = ReaderMetaclass

    section = None

    def __init__(self, config):
        if isinstance(config, RawConfigParser):
            self._config = config
        else:
            self._config = RawConfigParser()
            self._config.readfp(config)

    def check_config(self):
        errors = []
        for option in self._options:
            try:
                option.fget(self)
            except Exception as exc:
                errors.append(exc)

        if errors:
            raise ConfigurationErrors(errors)


class DatabaseReader(Reader):
    section("database")
    host = Option(default="")
    port = Option(type=int, default=5432)
    database = Option(default="minv")
    user = Option(default="minv")
    password = Option(required=True)
