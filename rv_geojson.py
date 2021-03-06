"""
This script contains functions meant to be used
while manipulating geojson files for plotting.

Zoom functions were developed to work with plotly mapbox figures,
and there's no guarantee they would work with other mapping services.
"""

import numpy as np
# import geopy.distance


def filter(geojson: dict, idkey: str, must_equal: str) -> dict:
    """Returns a filtered copy of the dictionary
    
    Parameters
    --------
    geojson: dict, with geojson-format feature dictionaries
        including dict_keys(['type', 'geometry', 'properties', 'id'])
    idkey: str, the path to the key on which to apply the filtering
        in the format 'key_layer0.key_layer1.[...].key_layerN'
    must_equal: str, the value which features' idkey value must be equal to
        in order to be included in the output
    
    Returns
    --------
    geojson_filtered: dict with the same structure
    """
    idkey = idkey.split('.')
    out = {'type': geojson['type']}
    out['features'] = []
    for feat in geojson['features']:
        val = feat
        for key in idkey:
            val = val[key]
        if val == must_equal:
            # out.append(feat)
            out['features'].append(feat)
    return out


def flatten_list(L):
    for e in L:
        if isinstance(e[0], (float, int)):
            yield e
        else:
            yield from flatten_list(e)


def gen_geometries(geojson):
    for feat in geojson['features']:
        if feat['geometry']['type'] == 'GeometryCollection':
            geometries = feat['geometry']['geometries']
        else:
            geometries = [feat['geometry']]
        for geom in geometries:
            yield geom


def flatten_geometries(geojson: dict, format: str='lonlat',
        return_pairs: bool=True) -> (tuple, tuple, tuple):
    """Get a list of gps locations used in the polygons of a geojson.
    
    Parameters
    --------
    geojson: dict, with geojson-format feature dictionaries
        including dict_keys(['type', 'geometry', 'properties', 'id'])
    format: str, specifying the order of longitude and latitude dimensions,
        expected values: 'lonlat' or 'latlon'
    
    Returns
    --------
    lons: tuple
    lats: tuple
    pairs: tuple, gps locations, only if `return_pairs==True`
    """
    if format not in ['lonlat', 'lanlot']:
        raise NotImplementedError(
            f"<format> must be one of ['lonlat', 'latlon'], got {format}"
        )
    if len(geojson['features']) == 0:
        print(geojson['features'])
        raise ValueError('geojson contains zero features')
    pairs = []
    for geom in gen_geometries(geojson):
        pairs.extend(list(flatten_list(geom['coordinates'])))
    if format == 'lonlat':
        lons, lats = zip(*pairs)
    else:
        lats, lons = zip(*pairs)
    if return_pairs:
        return lons, lats, pairs
    else:
        return lons, lats


def get_zoom_mercator(minlon, maxlon, minlat, maxlat, width_to_height):
    # longitudinal range by zoom level (20 to 1)
    # in degrees, if centered at equator
    lon_zoom_range = np.array([
        0.0007, 0.0014, 0.003, 0.006, 0.012, 0.024, 0.048, 0.096,
        0.192, 0.3712, 0.768, 1.536, 3.072, 6.144, 11.8784, 23.7568,
        47.5136, 98.304, 190.0544, 360.0
    ])
    margin = 1.2
    height = (maxlat - minlat) * margin * width_to_height
    width = (maxlon - minlon) * margin
    lon_zoom = np.interp(width , lon_zoom_range, range(20, 0, -1))
    lat_zoom = np.interp(height, lon_zoom_range, range(20, 0, -1))
    return round(min(lon_zoom, lat_zoom), 2)



def zoom_center(lons: tuple=None, lats: tuple=None, lonlats: tuple=None,
        format: str='lonlat', projection: str='mercator',
        width_to_height: float=2.0) -> (float, dict):
    """Finds optimal zoom and centering for a plotly mapbox.
    Must be passed (lons & lats) or lonlats.
    Temporary solution awaiting official implementation, see:
    https://github.com/plotly/plotly.js/issues/3434
    
    Parameters
    --------
    lons: tuple, optional, longitude component of each location
    lats: tuple, optional, latitude component of each location
    lonlats: tuple, optional, gps locations
    format: str, specifying the order of longitude and latitude dimensions,
        expected values: 'lonlat' or 'latlon', only used if passed lonlats
    projection: str, only accepting 'mercator' at the moment,
        raises `NotImplementedError` if other is passed
    width_to_height: float, expected ratio of final graph's with to height,
        used to select the constrained axis.
    
    Returns
    --------
    zoom: float, from 1 to 20
    center: dict, gps position with 'lon' and 'lat' keys

    >>> print(zoom_center((-109.031387, -103.385460),
    ...     (25.587101, 31.784620)))
    (5.75, {'lon': -106.208423, 'lat': 28.685861})
    """
    if lons is None and lats is None:
        if isinstance(lonlats, tuple):
            lons, lats = zip(*lonlats)
        else:
            raise ValueError(
                'Must pass lons & lats or lonlats'
            )
    
    # print(*map(type, (lons, lats, lonlats)))
    # input()
    
    maxlon, minlon = max(lons), min(lons)
    maxlat, minlat = max(lats), min(lats)
    center = {
        'lon': round((maxlon + minlon) / 2, 6),
        'lat': round((maxlat + minlat) / 2, 6)
    }
    
    if projection == 'mercator':
        zoom = get_zoom_mercator(minlon, maxlon, minlat, maxlat, width_to_height)
    else:
        raise NotImplementedError(
            f'{projection} projection is not implemented'
        )
        # # geopy uses 'latlon' format
        # height = geopy.distance.distance((maxlat, 0), (minlat, 0)).km
        # width = geopy.distance.distance((maxlat, minlon), (maxlat, maxlon)).km
        # # convert back to degrees, as if it were centered at equator
        # ...
        # # get zoom
        # lon_zoom = np.interp(height, lon_zoom_range, range(20, 0, -1))
        # lat_zoom = np.interp(width , lon_zoom_range, range(20, 0, -1))
    
    return zoom, center


def get_box(geojson: dict, format: str='lonlat') \
        -> ((float, float), (float, float)):
    """
    
    Parameters
    --------
    geojson: dict, with geojson-format feature dictionaries
        including dict_keys(['type', 'geometry', 'properties', 'id'])
    format: str, specifying the order of longitude and latitude dimensions,
        expected values: 'lonlat' or 'latlon'
    
    Returns
    --------
    a tuple of tuples containing ((minlon, maxlon), (minlat, maxlat))
    minlon: float
    maxlon: float
    minlat: float
    maxlat: float
    """
    if format not in ['lonlat', 'lanlot']:
        raise NotImplementedError(
            f"<format> must be one of ['lonlat', 'latlon'], got {format}"
        )
    if len(geojson['features']) == 0:
        print(geojson['features'])
        raise ValueError('geojson contains zero features')
    minlon = minlat = 180
    maxlon = maxlat = -180
    
    for geom in gen_geometries(geojson):
        for p in flatten_list(geom['coordinates']):
            if minlon > p[0]:
                minlon = p[0]
            elif maxlon < p[0]:
                maxlon = p[0]
            if minlat > p[1]:
                minlat = p[1]
            elif maxlat < p[1]:
                maxlat = p[1]
    
    if format == 'lonlat':
        return ((minlon, maxlon), (minlat, maxlat))
    else:
        return ((minlat, maxlat), (minlon, maxlon))


def zoom_on_box(box: ((float, float), (float, float)),
        format: str='lonlat', width_to_height: float=2.0) -> (float, dict):
    """Finds optimal zoom and centering for a plotly mapbox.
    Designed to work with `get_box` from same module.
    Temporary solution awaiting official implementation, see:
    https://github.com/plotly/plotly.js/issues/3434
    
    Parameters
    --------
    
    format: str, specifying the order of longitude and latitude dimensions,
        expected values: 'lonlat' or 'latlon', only used if passed lonlats
    width_to_height: float, expected ratio of final graph's with to height,
        used to select the constrained axis.
    
    Returns
    --------
    zoom: float, from 1 to 20
    center: dict, gps position with 'lon' and 'lat' keys

    >>> print(zoom_center((-109.031387, -103.385460),
    ...     (25.587101, 31.784620)))
    (5.75, {'lon': -106.208423, 'lat': 28.685861})
    """
    if format == 'lonlat':
        (minlon, maxlon), (minlat, maxlat) = box
    elif format == 'latlon':
        (minlon, maxlon), (minlat, maxlat) = box
    else:
        raise ValueError(
            'Expected "lonlat" or "latlon" in format,'
            f' "{format}" was passed'
        )
    center = {
        'lon': round((maxlon + minlon) / 2, 6),
        'lat': round((maxlat + minlat) / 2, 6)
    }
    zoom = get_zoom_mercator(minlon, maxlon, minlat, maxlat, width_to_height)
    return zoom, center


if __name__ == '__main__':
    
    
    import doctest
    # doctest.testmod(verbose=True)
    print(doctest.testmod())