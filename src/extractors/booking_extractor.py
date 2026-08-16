"""
Booking.com NO ofrece una API pública de autoservicio para desarrolladores
o investigadores individuales. Su "Booking.com Demand API" / Partner API
solo está disponible para partners aprobados (agencias de viaje, OTAs,
hoteles) mediante un proceso de solicitud comercial — no es viable para un
TFM académico en la mayoría de los casos.

Scrapear booking.com directamente incumple sus Términos de Servicio, así
que este módulo NO implementa scraping.

Alternativas honestas para aproximar "oferta hotelera" en tu dashboard:
  1. INE — Encuesta de Ocupación en Alojamientos Turísticos (EOAT):
     plazas, establecimientos y ocupación por provincia/CCAA (ver
     ine_extractor.py, buscando la operación "Ocupación").
  2. OSM Overpass (osm_extractor.py) — nº de alojamientos (tourism=hotel,
     guest_house, hostel, apartment) geolocalizados por municipio.
  3. Datasets ya publicados en datos.gob.es o Kaggle sobre precios/oferta
     hotelera (datosgob_extractor.py te ayuda a localizarlos).
  4. Si el TFM lo justifica, solicitar acceso a Booking Partner Hub
     (proceso de aprobación, no inmediato): https://partner.booking.com/

Se deja esta clase como placeholder para que el pipeline no rompa si se
referencia esta fuente, y para documentar la decisión metodológica en la
memoria del TFM.
"""


class BookingExtractor:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "Booking.com no dispone de API pública de autoservicio. "
            "Consulta el docstring de este módulo para alternativas "
            "(INE EOAT, OSM Overpass, datos.gob.es, o solicitud formal "
            "de acceso a Booking Partner Hub)."
        )
