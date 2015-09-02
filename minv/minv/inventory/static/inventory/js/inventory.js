

$(function() {

  /* OL 3 control to enable/disable drawing of the BBox */
  var EnableBBoxDraw = function(options) {
    options = options || {};

    var checkbox = document.createElement('input');
    checkbox.className = 'enable-draw';
    checkbox.setAttribute('type', 'checkbox');
    checkbox.checked = false;

    var inner = document.createElement('div');
    inner.appendChild(document.createTextNode("draw bbox"));
    inner.appendChild(checkbox);

    var element = document.createElement('div');
    element.className = 'ol-unselectable ol-control enable-draw-control';
    element.appendChild(inner);

    /* events are caught outside of this scope */

    ol.control.Control.call(this, {
      element: element,
      target: options.target
    });
  };
  ol.inherits(EnableBBoxDraw, ol.control.Control);

  $('button[role="clear-button"]').click(function() {
    $(this).parent(/* span */).parent(/* input-group */).find("input, select").val("").trigger("change");
  });

  $('a[data-page]').click(function() {
    $('input[name="page"]').val($(this).data("page"));
    $('form').submit();
  });

  $('[data-map]').each(function() {
    createMap(this);
  });


  function createMap(target) {
    var $target = $(target);
    var $parent = $(target).parent();
    var projection = ol.proj.get('EPSG:4326');
    var size = ol.extent.getWidth(projection.getExtent()) / 256;
    var resolutions = new Array(18);
    var matrixIds = new Array(18);

    for (var z = 0; z < 18; ++z) {
      // generate resolutions and matrixIds arrays for this WMTS
      resolutions[z] = size / Math.pow(2, z+1);
      matrixIds[z] = z;
    }
    var attribution = new ol.control.Attribution({collapsible: false});
    var map = new ol.Map({
      target: target,
      controls: ol.control.defaults({attribution: false}).extend([attribution]),
      layers: [
        new ol.layer.Tile({
          source: new ol.source.WMTS({
            urls: [
              '//a.tiles.maps.eox.at/wmts/',
              '//b.tiles.maps.eox.at/wmts/',
              '//c.tiles.maps.eox.at/wmts/',
              '//d.tiles.maps.eox.at/wmts/',
              '//e.tiles.maps.eox.at/wmts/',
              '//f.tiles.maps.eox.at/wmts/',
            ],
            layer: "terrain-light",
            matrixSet: "WGS84",
            format: "image/png",
            projection: projection,
            tileGrid: new ol.tilegrid.WMTS({
              origin: ol.extent.getTopLeft(projection.getExtent()),
              resolutions: resolutions,
              matrixIds: matrixIds
            }),
            style: "default",
            attributions: [
              new ol.Attribution({
                html: "Data &copy; <a href=\"http://www.openstreetmap.org/copyright\" target=\"_blank\">OpenStreetMap</a> contributors and <a href=\"/map_attribution.html\">others</a>. Rendering &copy; <a href=\"http://maps.eox.at\" target=\"_blank\">EOX</a>."
              })
            ],
          })
        }),
        new ol.layer.Tile({
          source: new ol.source.WMTS({
            urls: [
              '//a.tiles.maps.eox.at/wmts/',
              '//b.tiles.maps.eox.at/wmts/',
              '//c.tiles.maps.eox.at/wmts/',
              '//d.tiles.maps.eox.at/wmts/',
              '//e.tiles.maps.eox.at/wmts/',
              '//f.tiles.maps.eox.at/wmts/',
            ],
            layer: "overlay",
            matrixSet: "WGS84",
            format: "image/png",
            projection: projection,
            tileGrid: new ol.tilegrid.WMTS({
              origin: ol.extent.getTopLeft(projection.getExtent()),
              resolutions: resolutions,
              matrixIds: matrixIds
            }),
            style: "default",
            attributions: [
              new ol.Attribution({
                html: "Data &copy; <a href=\"http://www.openstreetmap.org/copyright\" target=\"_blank\">OpenStreetMap</a> contributors and <a href=\"/map_attribution.html\">others</a>. Rendering &copy; <a href=\"http://maps.eox.at\" target=\"_blank\">EOX</a>."
              })
            ],
          })
        })
      ],
      view: new ol.View({
        projection: projection,
        center: [0, 0],
        zoom: 2,
        maxZoom: 9,
        minZoom: 1,
        extent: [-180, -90, 180, 90]
      })
    });

    var vectorSource = new ol.source.Vector();
    map.addLayer(new ol.layer.Vector({source: vectorSource}));

    var dragBox = new ol.interaction.DragBox({
      style: new ol.style.Style({
        stroke: new ol.style.Stroke({
          color: [0, 0, 255, 1]
        })
      })
    });

    map.addControl(new EnableBBoxDraw());
    map.addInteraction(dragBox);
    dragBox.setActive(false);

    // activate/deactivate bbox drawing
    $target.find(".enable-draw").change(function() {
      dragBox.setActive($(this).is(":checked"));
    });

    // starting drawing a box
    dragBox.on('boxstart', function() {
      vectorSource.clear();
    });

    // finished drawing a box
    dragBox.on('boxend', function() {
      var geom = dragBox.getGeometry();
      var feature = new ol.Feature();
      feature.setGeometry(geom);
      vectorSource.addFeature(feature);
      var extent = geom.getExtent();
      
      $parent.find("input[name='minlat']").val(extent[1]);
      $parent.find("input[name='minlon']").val(extent[0]);
      $parent.find("input[name='maxlat']").val(extent[3]);
      $parent.find("input[name='maxlon']").val(extent[2]);
    });
    
    // listen on changes in the adjacent inputs
    $parent.find('input[type="text"]').change(function() {
      vectorSource.clear();
      var minlat = parseFloat($parent.find("input[name='minlat']").val());
      var minlon = parseFloat($parent.find("input[name='minlon']").val());
      var maxlat = parseFloat($parent.find("input[name='maxlat']").val());
      var maxlon = parseFloat($parent.find("input[name='maxlon']").val());

      if (isNaN(minlat) || isNaN(minlon) || isNaN(maxlat) || isNaN(maxlon)) {
        return;
      };

      var polygon = new ol.geom.Polygon([[
        [minlon, minlat], [maxlon, minlat], [maxlon, maxlat],
        [minlon, maxlat], [minlon, minlat]
      ]]);
      var feature = new ol.Feature();
      feature.setGeometry(polygon);
      vectorSource.addFeature(feature);
    });

    // shim to work around invisibility bug in Bootstrap tabs
    $("a[data-toggle='tab'][href='#parameters']").on("shown.bs.tab", function() {
      map.setTarget(target);
    });

    return map;
  }
});