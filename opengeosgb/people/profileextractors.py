from geonode.people.profileextractors import BaseExtractor


class GoogleExtractor(BaseExtractor):
    """
    Base class for social account data extractors.

    In order to define new extractors you just need to define a class that
    implements:

    * Some of the method stubs defined below - you don't need to implement
      all of them, just use the ones you need;

    In the spirit of duck typing, your custom class does not even need to
    inherit from this one. As long as it provides the expected methods
    geonode should be able to use it.

    Be sure to let geonode know about any custom adapters that you define by
    updating the ``SOCIALACCOUNT_PROFILE_EXTRACTORS`` setting.
    """
    def extract_area(self, data):
        raise NotImplementedError

    def extract_city(self, data):
        raise NotImplementedError

    def extract_country(self, data):
        raise NotImplementedError

    def extract_delivery(self, data):
        raise NotImplementedError

    def extract_email(self, data):
        raise NotImplementedError

    def extract_fax(self, data):
        raise NotImplementedError

    def extract_first_name(self, data):
        raise NotImplementedError

    def extract_last_name(self, data):
        raise NotImplementedError

    def extract_organization(self, data):
        raise NotImplementedError

    def extract_position(self, data):
        raise NotImplementedError

    def extract_profile(self, data):
        raise NotImplementedError

    def extract_voice(self, data):
        raise NotImplementedError

    def extract_zipcode(self, data):
        raise NotImplementedError

    def extract_email(self, data):
        return data.get("email", "")

    def extract_first_name(self, data):
        return data.get("name", "")

    def extract_last_name(self, data):
        return data.get("family_name", "")
