import * as GeoJSON from 'geojson';

/**
 * 计算GeoJSON几何对象的重心(centroid)
 * @param geoJson GeoJSON对象
 * @returns 重心坐标 [经度, 纬度]
 */
export function calculateGeoJsonCentroid(geoJson: GeoJSON.GeoJSON): [number, number] {
  if (!geoJson || !geoJson.type) {
    throw new Error('Invalid GeoJSON object');
  }

  switch (geoJson.type) {
    case 'Point':
      return calculatePointCentroid(geoJson as GeoJSON.Point);
    case 'MultiPoint':
    case 'LineString':
      return calculateLineCentroid(geoJson as GeoJSON.LineString | GeoJSON.MultiPoint);
    case 'MultiLineString':
    case 'Polygon':
      return calculatePolygonCentroid(geoJson as GeoJSON.Polygon | GeoJSON.MultiLineString);
    case 'MultiPolygon':
      return calculateMultiPolygonCentroid(geoJson as GeoJSON.MultiPolygon);
    case 'GeometryCollection':
      return calculateGeometryCollectionCentroid(geoJson as GeoJSON.GeometryCollection);
    case 'Feature':
      return calculateGeoJsonCentroid((geoJson as GeoJSON.Feature).geometry);
    case 'FeatureCollection':
      return calculateFeatureCollectionCentroid(geoJson as GeoJSON.FeatureCollection);
    default:
      if (typeof geoJson === 'object' && geoJson !== null && 'type' in geoJson) {
        throw new Error(`Unsupported GeoJSON type: ${(geoJson as { type: string }).type}`);
      } else {
        throw new Error('Unsupported GeoJSON object');
      }
  }
}

// 计算点类型的重心
function calculatePointCentroid(point: GeoJSON.Point): [number, number] {
  return [...point.coordinates] as [number, number];
}

// 计算线或多点类型的重心
function calculateLineCentroid(line: GeoJSON.LineString | GeoJSON.MultiPoint): [number, number] {
  const coords = line.coordinates;
  let x = 0;
  let y = 0;
  const len = coords.length;

  for (let i = 0; i < len; i++) {
    x += coords[i][0];
    y += coords[i][1];
  }

  return [x / len, y / len];
}

// 计算多边形或多线类型的重心
function calculatePolygonCentroid(polygon: GeoJSON.Polygon | GeoJSON.MultiLineString): [number, number] {
  const coords = polygon.type === 'Polygon' ? polygon.coordinates[0] : polygon.coordinates.flat();
  let x = 0;
  let y = 0;
  const len = coords.length;

  for (let i = 0; i < len; i++) {
    x += coords[i][0];
    y += coords[i][1];
  }

  return [x / len, y / len];
}

// 计算多多边形类型的重心
function calculateMultiPolygonCentroid(multiPolygon: GeoJSON.MultiPolygon): [number, number] {
  const coords = multiPolygon.coordinates.flatMap(poly => poly[0]);
  let x = 0;
  let y = 0;
  const len = coords.length;

  for (let i = 0; i < len; i++) {
    x += coords[i][0];
    y += coords[i][1];
  }

  return [x / len, y / len];
}

// 计算几何集合类型的重心
function calculateGeometryCollectionCentroid(collection: GeoJSON.GeometryCollection): [number, number] {
  const centroids = collection.geometries.map(geom => calculateGeoJsonCentroid(geom));
  let x = 0;
  let y = 0;
  const len = centroids.length;

  for (let i = 0; i < len; i++) {
    x += centroids[i][0];
    y += centroids[i][1];
  }

  return [x / len, y / len];
}

// 计算要素集合类型的重心
function calculateFeatureCollectionCentroid(featureCollection: GeoJSON.FeatureCollection): [number, number] {
  const centroids = featureCollection.features.map(feature => calculateGeoJsonCentroid(feature.geometry));
  let x = 0;
  let y = 0;
  const len = centroids.length;

  for (let i = 0; i < len; i++) {
    x += centroids[i][0];
    y += centroids[i][1];
  }

  return [x / len, y / len];
}