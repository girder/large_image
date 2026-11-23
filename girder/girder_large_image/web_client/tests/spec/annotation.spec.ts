import { expect, Page, test } from '@playwright/test';

import { asyncRestRequest, createUser } from '../util';
import { setupServer } from '../server';

/**
 * Ported from girder_annotation/test_annotation/web_client_specs/annotationSpec.js.
 *
 * The original spec was mostly a unit test of the annotation geometry, style,
 * and conversion helpers along with the AnnotationModel.  Those helpers are
 * exercised here by running them inside the page via page.evaluate and
 * asserting on the returned values.
 */

/**
 * Compute the l_inf distance from a to b.
 */
function dist(a: number[][], b: number[][]) {
  let max = 0;
  if (a.length !== b.length) {
    return Number.POSITIVE_INFINITY;
  }
  for (let i = 0; i < a.length; i += 1) {
    const dx = a[i][0] - b[i][0];
    const dy = a[i][1] - b[i][1];
    max = Math.max(max, dx * dx + dy * dy);
  }
  return Math.sqrt(max);
}

function expectClose(a: number[][], b: number[][], eps = 1e-6) {
  const d = dist(a, b);
  expect(Number.isNaN(d)).toBe(false);
  expect(d).toBeLessThan(eps);
}

/**
 * Convert an element with one of the geometry helpers and return the result.
 */
const geometry = (page: Page, kind: string, element: Record<string, unknown>) =>
  page.evaluate(({ kind, element }) => {
    const largeImageAnnotation = (window as any).girder.plugins.large_image_annotation;
    return largeImageAnnotation.annotations.geometry[kind](element);
  }, { kind, element });

const style = (page: Page, record: Record<string, unknown>) =>
  page.evaluate((record) => {
    const largeImageAnnotation = (window as any).girder.plugins.large_image_annotation;
    return largeImageAnnotation.annotations.style(record);
  }, record);

const convert = (page: Page, elements: Record<string, unknown>[]) =>
  page.evaluate((elements) => {
    const largeImageAnnotation = (window as any).girder.plugins.large_image_annotation;
    return largeImageAnnotation.annotations.convert(elements);
  }, elements);

test.describe('Annotations', () => {
  setupServer();

  test('geometry', async ({ page }) => {
    await test.step('rectangle', async () => {
      let obj = await geometry(page, 'rectangle', {
        type: 'rectangle',
        id: 'a',
        center: [10, 20, 0],
        width: 5,
        height: 10,
        rotation: 0,
      });
      expect(obj.type).toBe('Polygon');
      expect(obj.coordinates.length).toBe(1);
      expect(obj.annotationType).toBe('rectangle');
      expectClose(obj.coordinates[0], [
        [7.5, 15], [12.5, 15], [12.5, 25], [7.5, 25], [7.5, 15],
      ]);

      obj = await geometry(page, 'rectangle', {
        type: 'rectangle',
        id: 'a',
        center: [10, 10, 0],
        width: Math.sqrt(2),
        height: Math.sqrt(2),
        rotation: Math.PI / 4,
      });
      expect(obj.type).toBe('Polygon');
      expect(obj.coordinates.length).toBe(1);
      expect(obj.annotationType).toBe('rectangle');
      expectClose(obj.coordinates[0], [
        [10, 9], [11, 10], [10, 11], [9, 10], [10, 9],
      ]);
    });

    await test.step('open polyline', async () => {
      const obj = await geometry(page, 'polyline', {
        type: 'polyline',
        id: 'a',
        points: [[0, 1, 0], [1, 0, 0]],
        closed: false,
      });
      expect(obj.type).toBe('LineString');
      expect(obj.coordinates.length).toBe(2);
      expect(obj.annotationType).toBe('line');
      expectClose(obj.coordinates, [[0, 1], [1, 0]]);
    });

    await test.step('closed polyline', async () => {
      const obj = await geometry(page, 'polyline', {
        type: 'polyline',
        id: 'a',
        points: [[0, 1, 0], [1, 0, 0], [1, 1, 0]],
        closed: true,
      });
      expect(obj.type).toBe('Polygon');
      expect(obj.coordinates.length).toBe(1);
      expect(obj.coordinates[0].length).toBe(4);
      expect(obj.annotationType).toBe('polygon');
      expectClose(obj.coordinates[0], [[0, 1], [1, 0], [1, 1], [0, 1]]);
    });

    await test.step('point', async () => {
      const obj = await geometry(page, 'point', {
        type: 'point',
        id: 'a',
        center: [1, 2, 0],
      });
      expect(obj.type).toBe('Point');
      expect(obj.annotationType).toBe('point');
      expect(obj.coordinates).toEqual([1, 2]);
    });

    await test.step('ellipse', async () => {
      const obj = await geometry(page, 'ellipse', {
        type: 'ellipse',
        id: 'a',
        center: [10, 20, 0],
        width: 5,
        height: 10,
        rotation: 0,
      });
      expect(obj.type).toBe('Polygon');
      expect(obj.coordinates.length).toBe(1);
      expect(obj.annotationType).toBe('ellipse');
      expectClose(obj.coordinates[0], [
        [7.5, 15], [12.5, 15], [12.5, 25], [7.5, 25], [7.5, 15],
      ]);
    });

    await test.step('circle', async () => {
      const obj = await geometry(page, 'circle', {
        type: 'circle',
        id: 'a',
        center: [10, 20, 0],
        radius: 5,
      });
      expect(obj.type).toBe('Polygon');
      expect(obj.coordinates.length).toBe(1);
      expect(obj.annotationType).toBe('circle');
      expectClose(obj.coordinates[0], [
        [5, 15], [15, 15], [15, 25], [5, 25], [5, 15],
      ]);
    });
  });

  test('heatmapColorTable', async ({ page }) => {
    const values = [0.508, 0.806, 0.311, 0.402, 0.535, 0.661, 0.866, 0.31, 0.241, 0.63, 0.555, 0.067, 0.668, 0.164, 0.512, 0.647, 0.501, 0.637, 0.498, 0.658, 0.332, 0.431, 0.053, 0.531];
    const tests = [{
      name: 'no parameters',
      record: {},
      result: {
        min: 0,
        max: null,
        color: { 0: { r: 0, g: 0, b: 0, a: 0 }, 1: { r: 1, g: 1, b: 0, a: 1 } },
      },
    }, {
      name: 'normalize range, one value',
      record: { normalizeRange: true, colorRange: ['red'], rangeValues: [0.5] },
      result: {
        min: 0,
        max: null,
        color: { 0: { r: 0, g: 0, b: 0, a: 0 }, 1: { r: 1, g: 1, b: 0, a: 1 }, 0.5: 'red' },
      },
    }, {
      name: 'normalize range, several values',
      record: {
        normalizeRange: true,
        colorRange: ['blue', 'red', 'green', 'white', 'black'],
        rangeValues: [-1, -0.2, 0.5, 1.1, 2],
      },
      result: {
        min: 0,
        max: null,
        color: { 0: 'red', 0.5: 'green', 1: 'white' },
      },
    }, {
      name: 'no normalize range',
      record: {},
      result: {
        min: 0,
        max: null,
        color: { 0: { r: 0, g: 0, b: 0, a: 0 }, 1: { r: 1, g: 1, b: 0, a: 1 } },
      },
    }, {
      name: 'set range',
      record: { colorRange: ['red', 'blue'], rangeValues: [0, 1] },
      result: {
        min: 0,
        max: 1,
        color: { 0: 'red', 1: 'blue' },
      },
    }, {
      name: 'set range, more values',
      record: { colorRange: ['red', 'blue', 'green'], rangeValues: [0, 0.2, 0.8] },
      result: {
        min: 0,
        max: 0.8,
        color: { 0: 'red', 0.25: 'blue', 1: 'green' },
      },
    }, {
      name: 'set range, more range',
      record: { colorRange: ['red', 'blue'], rangeValues: [0.8, 0.8] },
      result: {
        min: 0.8,
        max: 0.8,
        color: { 0: { r: 0, g: 0, b: 0, a: 0 }, 1: 'red' },
      },
    }];
    for (const entry of tests) {
      await test.step(entry.name, async () => {
        const obj = await page.evaluate(({ record, values }) => {
          const largeImageAnnotation = (window as any).girder.plugins.large_image_annotation;
          const heatmapColorTable = largeImageAnnotation.annotations.convertFeatures.heatmapColorTable;
          return heatmapColorTable(record, values);
        }, { record: entry.record, values });
        expect(obj.min).toBe(entry.result.min);
        expect(obj.max).toBe(entry.result.max);
        expect(obj.color).toEqual(entry.result.color);
      });
    }
  });

  test('style', async ({ page }) => {
    await test.step('color names', async () => {
      const obj = await style(page, { fillColor: 'red', lineColor: 'black' });
      expect(obj.fillColor).toBe('#ff0000');
      expect(obj.fillOpacity).toBe(1);
      expect(obj.strokeColor).toBe('#000000');
      expect(obj.strokeOpacity).toBe(1);
    });
    await test.step('hex colors', async () => {
      const obj = await style(page, { fillColor: '#ff0000', lineColor: '#00ff00' });
      expect(obj.fillColor).toBe('#ff0000');
      expect(obj.fillOpacity).toBe(1);
      expect(obj.strokeColor).toBe('#00ff00');
      expect(obj.strokeOpacity).toBe(1);
    });
    await test.step('rgba colors', async () => {
      const obj = await style(page, { fillColor: 'rgba(255,0,0,0.5)', lineColor: 'rgba(0,255,255,0.5)' });
      expect(obj.fillColor).toBe('#ff0000');
      expect(obj.fillOpacity).toBe(0.5);
      expect(obj.strokeColor).toBe('#00ffff');
      expect(obj.strokeOpacity).toBe(0.5);
    });
    await test.step('line width, no colors', async () => {
      const obj = await style(page, { lineWidth: 2 });
      expect(obj).toEqual({ strokeWidth: 2 });
    });
  });

  test('convert', async ({ page }) => {
    await test.step('rectangle', async () => {
      const element = {
        type: 'rectangle',
        id: 'a',
        center: [10, 20, 0],
        width: 5,
        height: 10,
        rotation: 0,
      };
      const obj = await convert(page, [element]);
      const features = obj.features;
      expect(obj.type).toBe('FeatureCollection');
      expect(features.length).toBe(1);
      expect(features[0].id).toBe('a');
      const properties = features[0].properties;
      expect(properties.strokeWidth).toBe(2);
      expect(properties.fillColor).toBe('#000000');
      expect(properties.fillOpacity).toBe(0);
      expect(properties.strokeColor).toBe('#000000');
      expect(properties.strokeOpacity).toBe(1);
      expect(properties.element.type).toEqual(element.type);
    });

    await test.step('polyline', async () => {
      const element = {
        type: 'polyline',
        id: 'a',
        points: [[0, 1, 0], [1, 0, 0]],
      };
      const obj = await convert(page, [element]);
      const features = obj.features;
      expect(obj.type).toBe('FeatureCollection');
      expect(features.length).toBe(1);
      expect(features[0].id).toBe('a');
      const properties = features[0].properties;
      expect(properties.strokeWidth).toBe(2);
      expect(properties.fillColor).toBe('#000000');
      expect(properties.fillOpacity).toBe(0);
      expect(properties.strokeColor).toBe('#000000');
      expect(properties.strokeOpacity).toBe(1);
      expect(properties.element.type).toEqual(element.type);
    });
  });

  test('CRUD', async ({ page }) => {
    await test.step('setup', async () => {
      // The first user is an admin; create an empty item in its public folder.
      await createUser(page, 'admin', 'admin@email.com', 'Admin', 'Admin', 'password');
      const user = await asyncRestRequest(page, { url: 'user/me' }) as Record<string, string>;
      const folders = await asyncRestRequest(page, {
        url: 'folder',
        data: { parentType: 'user', parentId: user._id, name: 'Public' },
      }) as Array<Record<string, string>>;
      expect(folders.length).toBe(1);
      const item = await asyncRestRequest(page, {
        url: 'item',
        method: 'POST',
        data: { folderId: folders[0]._id, name: 'Empty' },
      }) as Record<string, string>;
      const items = await asyncRestRequest(page, { url: 'item?text=empty' }) as Array<Record<string, string>>;
      expect(items.length).toBeGreaterThan(0);
      expect(items[0]._id).toBe(item._id);
      await page.evaluate((item) => {
        (window as any).__t = { item };
      }, item);
    });

    await test.step('create a new annotation', async () => {
      const result = await page.evaluate(async () => {
        const t = (window as any).__t;
        const largeImageAnnotation = (window as any).girder.plugins.large_image_annotation;
        const model = new largeImageAnnotation.models.AnnotationModel({ itemId: t.item._id });
        model.elements().add({
          center: [5, 5, 0],
          height: 1,
          rotation: 0,
          type: 'rectangle',
          width: 1,
        });
        const resp = await model.save();
        t.annotationId = model.id;
        return { id: model.id, elements: resp.annotation && resp.annotation.elements ? resp.annotation.elements.length : null };
      });
      expect(result.id).toBeDefined();
      expect(result.elements).toBe(1);
    });

    await test.step('fetch an existing annotation', async () => {
      const itemId = await page.evaluate(async () => {
        const t = (window as any).__t;
        const largeImageAnnotation = (window as any).girder.plugins.large_image_annotation;
        t.annotation = new largeImageAnnotation.models.AnnotationModel({ _id: t.annotationId });
        await t.annotation.fetch();
        return t.annotation.get('itemId');
      });
      expect(itemId).toBeDefined();
    });

    await test.step('update an existing annotation', async () => {
      const count = await page.evaluate(async () => {
        const t = (window as any).__t;
        t.annotation.elements().add({
          center: [10, 10, 0],
          height: 2,
          rotation: 0,
          type: 'rectangle',
          width: 2,
          label: {},
        });
        const resp = await t.annotation.save();
        return resp.annotation.elements.length;
      });
      expect(count).toBe(2);
    });

    await test.step('update a paged annotation', async () => {
      const hasElements = await page.evaluate(async () => {
        const t = (window as any).__t;
        t.annotation._pageElements = true;
        const resp = await t.annotation.save();
        return resp.annotation.elements !== undefined;
      });
      expect(hasElements).toBe(false);
    });

    await test.step('destroy an existing annotation', async () => {
      const active = await page.evaluate(async () => {
        const t = (window as any).__t;
        const largeImageAnnotation = (window as any).girder.plugins.large_image_annotation;
        await t.annotation.destroy();
        t.annotation = new largeImageAnnotation.models.AnnotationModel({ _id: t.annotationId });
        await t.annotation.fetch();
        return t.annotation.get('_active');
      });
      expect(active).toBe(false);
    });

    await test.step('delete an annotation without unbinding events', async () => {
      const result = await page.evaluate(async () => {
        const t = (window as any).__t;
        const largeImageAnnotation = (window as any).girder.plugins.large_image_annotation;
        const model = new largeImageAnnotation.models.AnnotationModel({ itemId: t.item._id });
        let eventCalled = false;
        model.listenTo(model, 'change', () => { eventCalled = true; });
        await model.save();
        const id = model.id;
        await model.delete();
        const model2 = new largeImageAnnotation.models.AnnotationModel({ _id: id });
        await model2.fetch();
        eventCalled = false;
        model.trigger('change');
        return { active: model2.get('_active'), eventCalled };
      });
      expect(result.active).toBe(false);
      expect(result.eventCalled).toBe(true);
    });

    await test.step('cannot create an annotation without an itemId', async () => {
      const threw = await page.evaluate(() => {
        const largeImageAnnotation = (window as any).girder.plugins.large_image_annotation;
        const model = new largeImageAnnotation.models.AnnotationModel();
        try {
          model.save();
        } catch (err) {
          return true;
        }
        return false;
      });
      expect(threw).toBe(true);
    });

    await test.step('get an annotation name', async () => {
      const name = await page.evaluate(() => {
        const t = (window as any).__t;
        const largeImageAnnotation = (window as any).girder.plugins.large_image_annotation;
        const model = new largeImageAnnotation.models.AnnotationModel({
          itemId: t.item._id,
          annotation: { name: 'test annotation' },
        });
        return model.name();
      });
      expect(name).toBe('test annotation');
    });

    await test.step('create a large annotation', async () => {
      const result = await page.evaluate(async () => {
        const t = (window as any).__t;
        const largeImageAnnotation = (window as any).girder.plugins.large_image_annotation;
        const model = new largeImageAnnotation.models.AnnotationModel({ itemId: t.item._id });
        for (let i = 0; i < 1000; i += 1) {
          model.elements().add({
            center: [5 + (i % 100), 5 + Math.round(i / 100), 0],
            height: 1 + (i % 4),
            rotation: 0,
            type: 'rectangle',
            width: 1 + (i % 5),
          });
        }
        const resp = await model.save();
        t.annotationId = model.id;
        return { id: model.id, elements: resp.annotation.elements.length };
      });
      expect(result.id).toBeDefined();
      expect(result.elements).toBe(1000);
    });

    await test.step('fetch a paged annotation', async () => {
      const result = await page.evaluate(async () => {
        const t = (window as any).__t;
        const largeImageAnnotation = (window as any).girder.plugins.large_image_annotation;
        const annotation = new largeImageAnnotation.models.AnnotationModel({
          _id: t.annotationId, maxDetails: 100, minElements: 1, maxCentroids: 500,
        });
        const fetched = new Promise<void>((resolve) => {
          annotation.once('g:fetched', () => resolve());
        });
        await annotation.fetch();
        await fetched;
        return {
          itemId: annotation.get('itemId'),
          hasCentroids: annotation._centroids !== undefined,
          hasPartial: annotation._centroids !== undefined && annotation._centroids.partial !== undefined,
        };
      });
      expect(result.itemId).toBeDefined();
      expect(result.hasCentroids).toBe(true);
      expect(result.hasPartial).toBe(true);
    });
  });
});
