import { expect, Page, test } from '@playwright/test';

import { setupServer } from '../server';

/**
 * Ported from girder_annotation/test_annotation/web_client_specs/geojsAnnotationSpec.js.
 *
 * These are unit tests of the conversion between geojs annotations and
 * large_image annotation elements.  They run the conversion code inside the
 * page and assert on the returned values.
 */

const fillColor = 'rgba(0,0,0,0)';
const lineColor = 'rgb(0,0,0)';
const lineWidth = 2;

/**
 * Convert a mock geojs annotation of the given type and coordinates with the
 * named converter (or with the generic geojs.convert when no name is given).
 */
const convertGeojs = (page: Page, type: string, coordinates: unknown, converter?: string) =>
  page.evaluate(({ type, coordinates, converter }) => {
    const geojs = (window as any).girder.plugins.large_image_annotation.annotations.geojs;
    const style = { fill: false, stroke: false };
    const annotation = {
      type: () => type,
      options: () => ({ style }),
      coordinates: () => coordinates,
      style: (key: string) => (style as any)[key],
    };
    try {
      return { result: converter ? geojs.types[converter](annotation) : geojs.convert(annotation) };
    } catch (err) {
      return { error: `${err}` };
    }
  }, { type, coordinates, converter });

test.describe('geojs-annotations', () => {
  setupServer();

  test('convert from', async ({ page }) => {
    // invalid type
    expect((await convertGeojs(page, 'not valid', undefined)).error).toBeDefined();

    expect((await convertGeojs(page, 'point', [{ x: 0, y: 0 }])).result).toEqual({
      type: 'point',
      center: [0, 0, 0],
      fillColor,
      lineColor,
      lineWidth,
    });
  });

  test('convert to', async ({ page }) => {
    const results = await page.evaluate(() => {
      const convert = (window as any).girder.plugins.large_image_annotation.annotations.convert;
      return [
        convert({ attributes: { type: 'point', center: [0, 0, 0] } }),
        convert({ attributes: { type: 'point', center: [0, 0, 0] }, attributes2: { type: 'point', center: [0, 0, 0] } }),
        convert({ attributes: { type: 'point', center: [0, 0, 0] }, _attributes: { type: 'point', center: [0, 0, 0] } }),
      ].map((result) => ({ type: result.type, count: result.features.length }));
    });
    expect(results).toEqual([
      { type: 'FeatureCollection', count: 1 },
      { type: 'FeatureCollection', count: 2 },
      { type: 'FeatureCollection', count: 1 },
    ]);
  });

  test('coordinates', async ({ page }) => {
    const results = await page.evaluate(() => {
      const geojs = (window as any).girder.plugins.large_image_annotation.annotations.geojs;
      return {
        point2d: geojs.coordinates.point({ x: 1, y: 2 }),
        point3d: geojs.coordinates.point({ x: 1, y: 2, z: 3 }),
        array2d: geojs.coordinates.array([{ x: 1, y: 2 }]),
        array3d: geojs.coordinates.array([{ x: 1, y: 2, z: 3 }, { x: 2, y: 3, z: 4 }]),
      };
    });
    expect(results.point2d).toEqual([1, 2, 0]);
    expect(results.point3d).toEqual([1, 2, 3]);
    expect(results.array2d).toEqual([[1, 2, 0]]);
    expect(results.array3d).toEqual([[1, 2, 3], [2, 3, 4]]);
  });

  test('text', async ({ page }) => {
    await test.step('sanitizeText', async () => {
      const inputs: Array<[unknown, boolean?]> = [
        ['A comment'],
        ['  trimmed \n'],
        ['  not trimmed ', false],
        [undefined],
        [null],
        [5],
        [' \t\n '],
        ['two\nlines'],
        ['a\r\nb\rc\n\nd'],
        ['a\tb'],
        ['bell\u0007 del\u007f c1\u0085 nul\u0000.'],
        ['Ångström 日本語 😃 a b'],
      ];
      const results = await page.evaluate((inputs) => {
        const text = (window as any).girder.plugins.large_image_annotation.annotations.text;
        return inputs.map(([value, trim]) => (trim === undefined ? text.sanitizeText(value) : text.sanitizeText(value, trim)));
      }, inputs);
      expect(results).toEqual([
        'A comment',
        'trimmed',
        '  not trimmed ',
        '',
        '',
        '5',
        '',
        // line breaks are kept as line feeds, tabs become spaces, and other
        // control characters are removed
        'two\nlines',
        'a\nb\nc\n\nd',
        'a b',
        'bell del c1 nul.',
        // other unicode is kept, including characters outside of the basic
        // multilingual plane and non-breaking spaces within text
        'Ångström 日本語 😃 a b',
      ]);
    });

    await test.step('textFont', async () => {
      const results = await page.evaluate(() => {
        const text = (window as any).girder.plugins.large_image_annotation.annotations.text;
        return [
          text.textFont({ fontSize: 20 }),
          text.textFont({}),
          text.textFont(),
          text.textFont({ fontSize: -5 }),
          text.textFont({ fontSize: 12.5 }),
        ];
      });
      expect(results).toEqual([
        '20px/25px sans-serif',
        '16px/20px sans-serif',
        '16px/20px sans-serif',
        '16px/20px sans-serif',
        '12.5px/15.63px sans-serif',
      ]);
    });

    await test.step('text is not converted to geojson', async () => {
      const count = await page.evaluate(() => {
        const convert = (window as any).girder.plugins.large_image_annotation.annotations.convert;
        return convert({ a: { type: 'text', center: [1, 2, 0], text: 'A comment' } }).features.length;
      });
      expect(count).toBe(0);
    });
  });

  test('types', async ({ page }) => {
    await test.step('point', async () => {
      expect((await convertGeojs(page, 'point', [{ x: 1, y: 2 }], 'point')).result).toEqual({
        type: 'point',
        center: [1, 2, 0],
        fillColor,
        lineColor,
        lineWidth,
      });
    });

    await test.step('rectangle', async () => {
      const expected = {
        type: 'rectangle',
        center: [2, 3, 0],
        width: 2,
        height: 2,
        rotation: 0,
        fillColor,
        lineColor,
        lineWidth,
        normal: [0, 0, 1],
      };
      expect((await convertGeojs(page, 'rectangle', [
        { x: 1, y: 2 }, { x: 1, y: 4 }, { x: 3, y: 4 }, { x: 3, y: 2 },
      ], 'rectangle')).result).toEqual(expected);
      expect((await convertGeojs(page, 'rectangle', [
        { x: 3, y: 2 }, { x: 3, y: 4 }, { x: 1, y: 4 }, { x: 1, y: 2 },
      ], 'rectangle')).result).toEqual(expected);
    });

    await test.step('rotated rectangle', async () => {
      expect((await convertGeojs(page, 'rectangle', [
        { x: 0, y: -1 }, { x: -1, y: 0 }, { x: 0, y: 1 }, { x: 1, y: 0 },
      ], 'rectangle')).result).toEqual({
        type: 'rectangle',
        center: [0, 0, 0],
        width: Math.sqrt(2),
        height: Math.sqrt(2),
        rotation: -Math.PI / 4,
        fillColor,
        lineColor,
        lineWidth,
        normal: [0, 0, 1],
      });
      const result = (await convertGeojs(page, 'rectangle', [
        { x: 1, y: 2 }, { x: 9, y: 8 }, { x: 5, y: 11 }, { x: -3, y: 5 },
      ], 'rectangle')).result;
      expect(result.rotation).toBeCloseTo(Math.atan2(3, 4));
    });

    await test.step('polygon', async () => {
      expect((await convertGeojs(page, 'polygon', [
        { x: 0, y: 0 }, { x: 1, y: 0 }, { x: 1, y: 1 }, { x: 0, y: 1 },
      ], 'polygon')).result).toEqual({
        type: 'polyline',
        closed: true,
        points: [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
        fillColor,
        lineColor,
        lineWidth,
      });
    });

    await test.step('line', async () => {
      expect((await convertGeojs(page, 'line', [
        { x: 0, y: 0 }, { x: 1, y: 0 },
      ], 'line')).result).toEqual({
        type: 'polyline',
        closed: false,
        points: [[0, 0, 0], [1, 0, 0]],
        fillColor,
        lineColor,
        lineWidth,
      });
    });

    await test.step('ellipse', async () => {
      expect((await convertGeojs(page, 'ellipse', [
        { x: 1, y: 2 }, { x: 1, y: 4 }, { x: 3, y: 4 }, { x: 3, y: 2 },
      ], 'ellipse')).result).toEqual({
        type: 'ellipse',
        center: [2, 3, 0],
        width: 2,
        height: 2,
        rotation: 0,
        fillColor,
        lineColor,
        lineWidth,
        normal: [0, 0, 1],
      });
    });

    await test.step('circle', async () => {
      expect((await convertGeojs(page, 'circle', [
        { x: 1, y: 2 }, { x: 1, y: 4 }, { x: 3, y: 4 }, { x: 3, y: 2 },
      ], 'circle')).result).toEqual({
        type: 'circle',
        center: [2, 3, 0],
        radius: 1,
        fillColor,
        lineColor,
        lineWidth,
      });
    });
  });
});
