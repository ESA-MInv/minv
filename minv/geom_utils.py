# ------------------------------------------------------------------------------
#
# Project: Master Inventory <http://github.com/ESA-MInv/minv>
# Authors: Martin Paces <martin.paces@eox.at>
#          Fabian Schindler <fabian.schindler@eox.at>
#
# ------------------------------------------------------------------------------
# Copyright (C) 2015 European Space Agency
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# ------------------------------------------------------------------------------


# We are using a lot of short variable names and we are fine with that.
# pylint: disable=C0103

from math import ceil, floor
from itertools import izip, chain
from collections import defaultdict


class GeometryError(ValueError):
    """ Base geometry error exception """
    pass


class PoleInsidePolygon(GeometryError):
    """ Exception raised when the polygon contains the pole. """
    def __init__(self, message=None):
        message = message or "Polygon contains the pole!"
        GeometryError.__init__(self, message)


class EmptyGeometry(GeometryError):
    """ Exception raised when the has no points."""
    def __init__(self, message=None):
        message = message or "The geometry is empty!"
        GeometryError.__init__(self, message)


class EmptyPolygon(EmptyGeometry):
    """ Exception raised when the has no points."""
    def __init__(self, message=None):
        message = message or "Polygon has an empty list of coordinates!"
        EmptyGeometry.__init__(self, message)


class EmptyMultiPolygon(EmptyGeometry):
    """ Exception raised when the has no points."""
    def __init__(self, message=None):
        message = message or "Multi polygon has no polygon!"
        EmptyGeometry.__init__(self, message)


class ZeroAreaPolygon(GeometryError):
    """ Exception raised when the has no points."""
    def __init__(self, message=None):
        message = message or "Zero area polygon!"
        GeometryError.__init__(self, message)


def parse_point(coords_str):
    """ Parse a string containing a white-space separated 2D point coordinates.
    """
    x, y = coords_str.split()
    return float(x), float(y)


def parse_coords(coords_str):
    """ Parse a string containing a white-space separated list of 2D
    coordinates. The function returns an iterator generating a sequence
    of pairs of coordinates.
    """
    itr = (float(v) for v in coords_str.split())
    return zip(itr, itr)


def parse_coords_list(coords_list_str, delimiter="|"):
    """ Parse a string containing a list of white-space separated list of 2D
    coordinates. The function returns a list of iterators generating a sequence
    of pairs of coordinates.
    """
    return [
        coord_list for coord_list in (
            parse_coords(item) for item in coords_list_str.split(delimiter)
        ) if coord_list
    ]


def format_point(x, y):
    """ Format 2D point coordinates to a string. """
    return "%.12g %.12g" % (x, y)


def format_coords(coords):
    """ Format sequence of 2D coordinates to a string. """
    return " ".join(format_point(x, y) for (x, y) in coords)


def format_coords_list(coords_list, delimiter="|"):
    """ Format list of sequences of 2D coordinates to a string. """
    return delimiter.join(
        coord_list_str for coord_list_str in (
            format_coords(item) for item in coords_list
        ) if coord_list_str
    )


def iter_closed_loop(coords):
    """ Generator iterating over the given coordinates assuring that the first
    and last coordinates are the same (closed loop).
    """
    it_coords = iter(coords)
    try:
        coord_first = coord = it_coords.next()
    except StopIteration:
        return
    yield coord_first
    for coord in it_coords:
        yield coord
    if coord_first != coord:
        yield coord_first


def translate_coords(coords, offset):
    """ Translate (move) coordinates by the given offset. """
    x_off, y_off = offset
    return [(x + x_off, y + y_off) for x, y in coords]


def translate_coords_list(coords_list, offset):
    """ Translate (move) coordinates by the given offset. """
    return [translate_coords(item, offset) for item in coords_list]


def wrap_period(value, period=1.0, base=0.0):
    """ Map arbitrary periodic coordinate `value` with period `period`
        to the base interval starting at `base`.
        E.g.:
            wrap_period(+181., 360., -180.0) --> -179.
            wrap_period(-181., 360., -180.0) --> +179.
    """
    tmp = (value - base) / period
    return (tmp - floor(tmp)) * period + base


def wrap_dateline(coords):
    """ Wrap coordinates around dateline so that they all lie within the
    -/+180 dg. bounds.
    This method will likely produce polygons with invalid geometry.
    The (latitude, longitude) coordinates must be in decimal degrees.
    """
    return [(y, wrap_period(x, 360., -180.)) for y, x in coords]


def crosses_dateline(coords, atol=1e-12):
    """ Detect a dateline crossing polygon.
    The (latitude, longitude) coordinates must be in decimal degrees.

    The detection algorithm is based on an assumption than no polygon edge
    can span over more than 180dg of longitude unless i) it lies directly
    on a pole or ii) connect the poles
    """
    def is_pole(x):
        return 90.0 - abs(x) <= atol
    # No assumption is made whether the loop is closed or not.
    it_coords = iter_closed_loop(coords)
    try:
        y0, x0 = it_coords.next()
    except StopIteration:
        raise EmptyPolygon
    for y1, x1 in it_coords:
        # Skip edges whose both ends lie on the same pole.
        if is_pole(y0) and is_pole(y1) and y0 * y1 > 0:
            continue
        dx0 = x1 - x0
        dx1 = wrap_period(dx0, 360., -180.)
        if abs(dx0) - abs(dx1) > atol:
            return True
        x0, y0 = x1, y1
    return False


def _polygon_unwrap_dateline(coords, atol=1e-12):
    """ Generate unwrapped dateline crossing polygon.
    The (latitude, longitude) coordinates must be in decimal degrees.

    The unwrapping algorithm is based on an assumption than no polygon edge
    can span over more than 180dg of longitude unless it lies directly
    on a pole.
    """
    def is_pole(x):
        return 90.0 - abs(x) <= atol
    # No assumptition is made whether the loop is closed or not.
    it_coords = iter_closed_loop(coords)
    try:
        y0, x0 = it_coords.next()
    except StopIteration:
        raise EmptyPolygon
    yield y0, x0
    period = 0
    for y1, x1 in it_coords:
        # Skip edges whose both ends lie on the same pole.
        if is_pole(y0) and is_pole(y1) and y0 * y1 > 0:
            continue
        dx0 = x1 - x0
        dx1 = wrap_period(dx0, 360., -180.)
        if abs(dx0) - abs(dx1) > atol:
            # NOTE: Rounding eliminates any possible rouding error.
            period += round(dx1 - dx0)
        yield y1, x1 + period
        x0, y0 = x1, y1
    if abs(period) > 0:
        raise PoleInsidePolygon(repr(list(coords)))


def polygon_unwrap_dateline(coords, atol=1e-12):
    """ Return list of coordinates of an unwrapped dateline crossing polygon.
    The (latitude, longitude) coordinates must be in decimal degrees.

    The unwrapping algorithm is based on an assumption than no polygon edge
    can span over more than 180dg of longitude unless it lies directly
    on a pole.
    """
    return list(_polygon_unwrap_dateline(coords, atol))


def polygon_wrap_dateline(coords, max_lon_bound=36180.0):
    """ Wrap polygon geometry around the dateline within the -/+180dg longitude
    bounds.
    The source geometry is encoded as a sequence of (latitude, longitude)
    coordinates in degrees.  The source polygon exceeding the maximum allowed
    longitude bounds -/+`max_lon_bound` is clipped.
    The produced multi-polygon is then encoded as a list of lists of
    coordinates. The produced polygons are not dissolved and may possibly
    overlap.
    """
    # pylint: disable=R0912
    # pylint: disable=R0914
    def get_period(lon):
        """ Get latitude period."""
        return int(
            floor(lon/360.0 + 0.5) if lon < 0.0 else ceil(lon/360.0 - 0.5)
        )

    def get_dateline_intersection((y0, x0), (y1, x1), period):
        """ Get intersection with the meridian at the given longitude. """
        xi = period * 360.0 - 180.0
        yi = y0 + (xi - x0)*(y1 - y0)/(x1 - x0)
        return (yi, xi)

    def connect_segments(segments, meridian):
        """ Connect loose segments. """
        lidx_i, lidx_o = [], []
        for idx, segment in enumerate(segments):
            if segment[0][1] == meridian:
                lidx_i.append((tuple(y for y, x in segment), idx))
            if segment[-1][1] == meridian:
                lidx_o.append((tuple(y for y, x in segment[::-1]), idx))
        assert len(lidx_i) == len(lidx_o)
        connections = [
            (idx_i, idx_o) for (_, idx_i), (_, idx_o)
            in izip(sorted(lidx_i), sorted(lidx_o))
        ]
        del lidx_i, lidx_o
        while connections:
            idx_i, idx_o = connections.pop()
            # connect segments' ends
            if segments[idx_o][-1] != segments[idx_i][0]:
                segments[idx_o].append(segments[idx_i][0])
            if idx_i != idx_o:
                # join two separate segments
                segments[idx_o].extend(segments[idx_i][1:])
                segments[idx_i] = None
                connections = [
                    (ii, idx_o if io == idx_i else ii) for ii, io in connections
                ]
        return [segment for segment in segments if segment is not None]

    period_bound = max(0, get_period(max_lon_bound))
    segments = defaultdict(list)
    # No assumption is made whether the loop is closed or not.
    it_coords = iter_closed_loop(coords)
    try:
        y0, x0 = it_coords.next()
    except StopIteration:
        raise EmptyPolygon
    # Split polygon to line segments.
    period = min(max(get_period(x0), -period_bound - 1), period_bound + 1)
    segment = [(y0, x0 - period * 360.0)]
    for y1, x1 in it_coords:
        period_new = get_period(x1)
        while (
                period != period_new and (
                    min(abs(period), abs(period_new)) <= period_bound or
                    (period * period_new) < 0
                )
           ):
            yi, xi = get_dateline_intersection(
                (y0, x0), (y1, x1), period + (period_new > period)
            )
            if (yi, xi) != (y0, x0):
                segment.append((yi, xi - period * 360.0))
            if abs(period) <= period_bound:
                segments[period].append(segment)
            segment = []
            period += -1 if period_new < period else 1
            if (yi, xi) != (y1, x1):
                segment.append((yi, xi - period * 360.0))
            x0, y0 = xi, yi
        segment.append((y1, x1 - period * 360.0))
        x0, y0 = x1, y1
    if abs(period) <= period_bound:
        segments[period].append(segment)
    # Connect line segments to polygons.
    polygons = []
    for period in segments:
        # join edges passing through the lower and upper bounds
        _segments = segments[period]
        _segments = connect_segments(_segments, -180.0)
        _segments = connect_segments(_segments, +180.0)
        polygons.extend(segment for segment in _segments if len(segment) > 3)
    return polygons


def _centroid(coords):
    """ Evaluate the integral contributions needed for evaluation of the
        polygon or multi-polygon centroid.
        Function throws an exception for degenerated zero area polygons.
    """
    # No assumption is made whether the loop is closed or not.
    it_coords = iter_closed_loop(coords)
    try:
        x0, y0 = it_coords.next()
    except StopIteration:
        raise EmptyPolygon
    sum_ = sumx = sumy = 0.0
    for x1, y1 in it_coords:
        tmp = x1*y0 - x0*y1
        sum_ += tmp
        sumx += tmp * (x0 + x1)
        sumy += tmp * (y0 + y1)
        x0, y0 = x1, y1
    if sum_ == 0.0:
        raise ZeroAreaPolygon
    sum_ *= 3.0
    return (sumx, sumy, sum_)


def polygon_centroid(coords):
    """ Calculate centroid of a polygon defined by a loop of coordinates.
        Function throws an exception for degenerated zero area polygons.
    """
    sumx, sumy, sum_ = _centroid(coords)
    return sumx / sum_, sumy / sum_


def multi_polygon_centroid(coords_list):
    """ Calculate centroid of a multi-polygon defined by a list of loops
        of coordinates.
        Function throws an exception for degenerated zero area polygons.
    """
    cnt, sumx, sumy, sum_ = 0, 0.0, 0.0, 0.0
    for coords in coords_list:
        try:
            sumx_tmp, sumy_tmp, sum__tmp = _centroid(coords)
        except EmptyPolygon:
            continue
        except ZeroAreaPolygon:
            cnt += 1
            continue
        cnt += 1
        sgn = +1.0 if sum__tmp >= 0.0 else -1.0
        sumx += sgn * sumx_tmp
        sumy += sgn * sumy_tmp
        sum_ += sgn * sum__tmp
    if cnt == 0:
        raise EmptyMultiPolygon
    if sum_ == 0.0:
        raise ZeroAreaPolygon
    return sumx / sum_, sumy / sum_


def footprint_to_scene_centre(coords_list):
    """ Convert index file 'footprint' to 'sceneCentre'. """
    if isinstance(coords_list, basestring):
        coords_list = parse_coords_list(coords_list)
    coords_list = [polygon_unwrap_dateline(coords) for coords in coords_list]
    y_cnt, x_cnt = multi_polygon_centroid(coords_list)
    x_cnt = wrap_period(x_cnt, 360., -180.)
    return format_point(y_cnt, x_cnt)


def fix_footprint(footprint, scene_centre=None, wrap_geometry=True):
    """ Unwrap the footprint and update footprint record.
    The function makes use if the scene centre if available.
    A pair of the new footprint and scene centre is returned.
    """
    if isinstance(footprint, basestring):
        footprint = parse_coords_list(footprint)
    if scene_centre and isinstance(scene_centre, basestring):
        scene_centre = parse_point(scene_centre)
    footprint = [polygon_unwrap_dateline(item) for item in footprint]
    if scene_centre is None:
        y_cnt, x_cnt = multi_polygon_centroid(footprint)
        x_cnt = wrap_period(x_cnt, 360., -180.)
        scene_centre = y_cnt, x_cnt
    else:
        y_cnt, x_cnt = scene_centre
    x_coords = [x for _, x in chain.from_iterable(footprint)]
    x_min, x_max = min(x_coords), max(x_coords)
    if x_min > x_cnt or x_max < x_cnt:
        offset = (0.0, -360.0 if x_min > x_cnt else +360.0)
        footprint = [translate_coords(item, offset) for item in footprint]
    if wrap_geometry:
        footprint = list(chain.from_iterable(
            polygon_wrap_dateline(item) for item in footprint
        ))
    return footprint, scene_centre


def coords2bbox(coords):
    """ Calculate a bounding box from a set of coordinates """
    tmp = zip(*coords)
    if len(tmp) == 0:
        raise EmptyGeometry
    coord_x, coord_y = tmp
    return BBox(min(coord_x), min(coord_y), max(coord_x), max(coord_y))


def coords_list2bbox(coords_list):
    """ Calculate a bounding box from a set of coordinates """
    return coords2bbox(chain.from_iterable(coords_list))


class BBox(tuple):
    """ 2D Bounding Box class """

    class NoOverlap(Exception):
        """ Exception raised when there is no overlap between bounding boxes.
        """
        pass

    # We are using a lot of short variable names and we are fine with that.
    # pylint: disable=C0103
    __slots__ = ()

    def __new__(cls, minx, miny, maxx, maxy):
        if (minx > maxx) or (miny > maxy):
            raise ValueError(
                "Invalid bounding box definition (%r, %r, %r %r)" %
                (minx, miny, maxx, maxy)
            )
        return tuple.__new__(
            cls, (float(minx), float(miny), float(maxx), float(maxy))
        )

    minx = property(lambda self: self[0])
    miny = property(lambda self: self[1])
    maxx = property(lambda self: self[2])
    maxy = property(lambda self: self[3])

    extent_x = property(lambda self: self[2] - self[0])
    extent_y = property(lambda self: self[3] - self[1])

    @property
    def coords(self):
        """ Get bounding box as list of lower-left and upper-right
        coordinates.
        """
        x0, y0, x1, y1 = self
        return [(x0, y0), (x1, y1)]

    @property
    def corners(self):
        """ Get bounding box as list of all four corner coordinates.
        """
        x0, y0, x1, y1 = self
        return [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]

    @property
    def ring(self):
        """ Get bounding box as list of all four corner coordinates
            encoded as closed loop, i.e., the last coordinate is the copy
            of the first one.
        """
        x0, y0, x1, y1 = self
        return [(x0, y0), (x0, y1), (x1, y1), (x1, y0), (x0, y0)]

    @property
    def swapped(self):
        """ Return bounding box instance with swapped axes.
        """
        x0, y0, x1, y1 = self
        return BBox(y0, x0, y1, x1)

    def contains(self, x, y=None):
        """ Test whether an (x, y) point is contained by the bounding box.
        """
        if y is None:
            x, y = x
        return (self[0] <= x <= self[2]) and (self[1] <= y <= self[3])

    def grow_by(self, factor):
        """ Enlarge the extent of the bounding box by a relative factor.
        E.g., 0.1 enlarges the box 10% in all directions.
        """
        gx = self.extent_x * factor
        gy = self.extent_y * factor
        return BBox(
            self.minx - gx, self.miny - gy, self.maxx + gx, self.maxy + gy
        )

    def clip(self, other):
        """ Get intersection of two boxes."""
        minx = max(self[0], other[0])
        miny = max(self[1], other[1])
        maxx = min(self[2], other[2])
        maxy = min(self[3], other[3])
        if (minx > maxx) or (miny > maxy):
            raise self.NoOverlap
        return BBox(minx, miny, maxx, maxy)

    def envelope(self, other):
        """ Get intersection of two boxes."""
        minx = min(self[0], other[0])
        miny = min(self[1], other[1])
        maxx = max(self[2], other[2])
        maxy = max(self[3], other[3])
        return BBox(minx, miny, maxx, maxy)

    def get_grid_cell_bbox(self, (nx, ny), (ix, iy)):
        """ Get bounding box of a (ix, iy)-cell of a regular (nx, ny) regular
        equidistant grid of the source box.
        """
        assert nx > 0
        assert ny > 0
        dx = self.extent_x / float(nx)
        dy = self.extent_y / float(ny)
        return BBox(
            self.minx + ix * dx, self.miny + iy * dy,
            self.minx + (ix+1) * dx, self.miny + (iy+1) * dy
        )

    def __repr__(self):
        return "BBox%s" % tuple.__repr__(self)
