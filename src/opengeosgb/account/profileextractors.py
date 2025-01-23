from geonode.people.profileextractors import OpenIDExtractor


class GovBRExtractor(OpenIDExtractor):
    def extract_voice(self, data):
        return data.get("phone_number", "")
    
    def extract_country(self, data):
        country = super().extract_country(data) 
        return country if country else "BRA"
