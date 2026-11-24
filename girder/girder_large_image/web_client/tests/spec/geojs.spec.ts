import { expect, Page, test } from '@playwright/test';

import { asyncRestRequest, createCollection, createUser, login, uploadTestFile, waitForIdlePage } from '../util';
import { setupServer } from '../server';

/**
 * Ported from girder_annotation/test_annotation/web_client_specs/geojsSpec.js.
 *
 * The original spec created a geojs image viewer widget directly in the
 * page and then drove it through a long sequence of Jasmine `it` blocks that
 * shared the viewer and several annotation models.  That sequence is
 * preserved here: the shared objects live in the page as `window.__t`, each
 * original `it` is a test.step, and the checks that need synchronous access
 * to geojs objects run inside the page via page.evaluate using the small
 * `window.__assert` helpers installed by installHelpers().  Anything thrown
 * inside page.evaluate fails the test with its message.
 *
 * The original used sinon for spies; `window.__spy` is a minimal equivalent
 * that counts calls.
 */

const ADMIN = {
  login: 'admin',
  email: 'admin@email.com',
  firstName: 'Admin',
  lastName: 'Admin',
  password: 'testpassword',
};

// Set by the setup test and reused by the viewer test.
let itemId = '';
let annotationId = '';
let overlayAnnotationId = '';

/**
 * Install the in-page helpers used by the viewer test.
 */
const installHelpers = async (page: Page, ids: Record<string, string>) => {
  await page.evaluate((ids) => {
    const w = window as any;
    const t: any = { ...ids };
    w.__t = t;

    w.__spy = (obj: any, name: string) => {
      const original = obj[name];
      const spy: any = function (this: unknown, ...args: unknown[]) {
        spy.callCount += 1;
        return original.apply(this, args);
      };
      spy.callCount = 0;
      spy.restore = () => { obj[name] = original; };
      obj[name] = spy;
      return spy;
    };

    const fail = (msg: string | undefined, detail: string) => {
      throw new Error(`${msg ? msg + ': ' : ''}${detail}`);
    };
    w.__assert = {
      eq: (a: unknown, b: unknown, msg?: string) => {
        if (a !== b) {
          fail(msg, `expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`);
        }
      },
      deepEq: (a: unknown, b: unknown, msg?: string) => {
        if (JSON.stringify(a) !== JSON.stringify(b)) {
          fail(msg, `expected ${JSON.stringify(b)}, got ${JSON.stringify(a)}`);
        }
      },
      ok: (v: unknown, msg?: string) => {
        if (!v) {
          fail(msg, `expected a truthy value, got ${JSON.stringify(v)}`);
        }
      },
      close: (a: number, b: number, precision = 6, msg?: string) => {
        if (!(Math.abs(a - b) < Math.pow(10, -precision) / 2)) {
          fail(msg, `expected ${a} to be close to ${b} (precision ${precision})`);
        }
      },
      closeTo: (a: number[], b: number[], tol = 6, msg?: string) => {
        w.__assert.eq(a.length, b.length, msg);
        for (let i = 0; i < a.length; i += 1) {
          w.__assert.close(a[i], b[i], tol, msg);
        }
      },
      greater: (a: number, b: number, msg?: string) => {
        if (!(a > b)) {
          fail(msg, `expected ${a} to be greater than ${b}`);
        }
      },
      match: (a: string, re: RegExp, msg?: string) => {
        if (!re.test(a)) {
          fail(msg, `expected ${JSON.stringify(a)} to match ${re}`);
        }
      },
    };

    // Helpers for the text element tests.
    t.clickAt = (x: number, y: number) => {
      const pt = t.viewer.viewer.gcsToDisplay({ x, y });
      t.interactor.simulateEvent('mousedown', { button: 'left', map: pt });
      t.interactor.simulateEvent('mouseup', { button: 'left', map: pt });
    };
    t.typeText = (text: string) => {
      const input = t.$el.find('.g-li-annotation-text-edit');
      w.__assert.eq(input.length, 1, 'text editor count');
      input.val(text).trigger('input');
      return input;
    };
    t.key = (input: any, name: string, ctrl?: boolean) => {
      input.trigger(w.girder.$.Event('keydown', { key: name, ctrlKey: !!ctrl }));
    };

    // Helper for the highlight and hide tests.
    t.checkFeatureOpacity = (annotationId: string, fillOpacity: number, strokeOpacity: number, filter?: (data: any) => boolean) => {
      const _ = w.girder._;
      filter = filter || (() => true);
      _.each(t.viewer._annotations[annotationId].features, (feature: any, findex: number) => {
        const fillOpacityFunction = feature.style.get('fillOpacity');
        const strokeOpacityFunction = feature.style.get('strokeOpacity');
        const allData = feature.data();
        _.each(_.filter(allData, filter), (data: any, index: number) => {
          w.__assert.eq(fillOpacityFunction(allData, findex, data, index), fillOpacity, `fill opacity of ${annotationId}`);
          w.__assert.eq(strokeOpacityFunction(allData, findex, data, index), strokeOpacity, `stroke opacity of ${annotationId}`);
        });
      });
    };
  }, ids);
};

/**
 * Create an annotation on the test item from within the page and return its
 * id.
 */
const createAnnotation = async (page: Page, annotation: Record<string, unknown>) => {
  const resp = await asyncRestRequest(page, {
    url: `annotation?itemId=${itemId}`,
    contentType: 'application/json',
    processData: false,
    type: 'POST',
    data: JSON.stringify(annotation),
  }) as Record<string, string>;
  return resp._id;
};

test.describe('Geojs viewer', () => {
  setupServer();
  test.describe.configure({ mode: 'serial' });

  test('setup: create an admin, upload an image, and create annotations', async ({ page }) => {
    await createUser(page, ADMIN.login, ADMIN.email, ADMIN.firstName, ADMIN.lastName, ADMIN.password);
    await page.locator('a.g-nav-link[g-target="collections"]').click();
    await expect(page.locator('.g-collection-create-button:visible')).toBeVisible();
    await expect(page.locator('.g-collection-list-entry')).toHaveCount(0);
    await createCollection(page, 'test', '', 'image');
    await uploadTestFile(page, 'small_la.tiff');
    const src = await page.locator('.large_image_thumbnail img').first().getAttribute('src');
    itemId = ((src || '').match(/\/item\/([^/]*)/) || [])[1];
    expect(itemId).toMatch(/^[0-9a-f]{24}$/);

    await test.step('upload test annotation', async () => {
      annotationId = await createAnnotation(page, {
        name: 'test annotation',
        elements: [{
          type: 'rectangle',
          center: [200, 200, 0],
          width: 400,
          height: 400,
          rotation: 0,
        }],
      });
      expect(annotationId).toBeDefined();
    });

    await test.step('upload test overlay annotation', async () => {
      overlayAnnotationId = await createAnnotation(page, {
        name: 'test overlay annotation',
        elements: [{
          type: 'image',
          girderId: itemId,
          opacity: 0.5,
          transform: {
            xoffset: 10,
            yoffset: 15,
          },
        }],
      });
      expect(overlayAnnotationId).toBeDefined();
    });
  });

  test('Geojs viewer', async ({ page }) => {
    await login(page, ADMIN.login, ADMIN.password);
    await installHelpers(page, { itemId, annotationId, overlayAnnotationId });

    await test.step('script is loaded', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const $ = w.girder.$;
        const GeojsViewer = w.girder.plugins.large_image.views.imageViewerWidget.geojs;
        t.$el = $('<div/>').appendTo('body').css({ width: '400px', height: '300px' });
        t.viewer = new GeojsViewer({
          el: t.$el,
          itemId: t.itemId,
          parentView: null,
          hoverEvents: true,
        });
      });
      await page.waitForFunction(() => document.querySelectorAll('.geojs-layer.active').length >= 1);
      const size = await page.evaluate(() => {
        const t = (window as any).__t;
        t.interactor = t.viewer.viewer.interactor();
        return t.viewer.viewer.size();
      });
      expect(size).toEqual({ width: 400, height: 300 });
    });

    await test.step('drawAnnotation', async () => {
      await page.evaluate(async () => {
        const w = window as any;
        const t = w.__t;
        const largeImageAnnotation = w.girder.plugins.large_image_annotation;
        t.annotation = new largeImageAnnotation.models.AnnotationModel({ _id: t.annotationId });
        await t.annotation.fetch();
        t.setViewSpy = w.__spy(t.annotation, 'setView');
        t.viewer.drawAnnotation(t.annotation);
        t.viewer.viewer.zoom(5);
      });
      await waitForIdlePage(page);
      await page.waitForFunction(() => {
        const t = (window as any).__t;
        return t.viewer._annotations[t.annotationId] && t.viewer._annotations[t.annotationId].features.length >= 1;
      });
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        assert.ok(t.viewer._annotations[t.annotationId], 'annotation record');
        // geojs makes two features for a polygon
        assert.ok(t.viewer._annotations[t.annotationId].features.length >= 1, 'feature count');
        t.featureSpy = w.__spy(t.viewer._annotations[t.annotationId].features[0], '_exit');
        assert.greater(t.setViewSpy.callCount, 0, 'setView called');
        const firstCount = t.setViewSpy.callCount;
        t.viewer.viewer.zoomRange({ max: 12 });
        t.viewer.viewer.zoom(12);
        t.viewer.viewer.zoom(1);
        assert.eq(t.setViewSpy.callCount, firstCount + 2, 'setView call count');
      });
    });

    await test.step('draw overlay', async () => {
      await page.evaluate(async () => {
        const w = window as any;
        const t = w.__t;
        const largeImageAnnotation = w.girder.plugins.large_image_annotation;
        t.overlayAnnotation = new largeImageAnnotation.models.AnnotationModel({ _id: t.overlayAnnotationId });
        await t.overlayAnnotation.fetch();
        t.projStringSpy = w.__spy(t.viewer, '_getOverlayTransformProjString');
        t.viewer.drawAnnotation(t.overlayAnnotation);
      });
      await waitForIdlePage(page);
      await page.waitForFunction(() => {
        const t = (window as any).__t;
        return !!t.viewer._annotations[t.overlayAnnotationId];
      });
      const callCount = await page.evaluate(() => (window as any).__t.projStringSpy.callCount);
      expect(callCount).toBe(1);
    });

    await test.step('set overlay opacity', async () => {
      await page.waitForFunction(() => {
        const t = (window as any).__t;
        const overlayId = t.viewer._annotations[t.overlayAnnotationId].overlays[0].id;
        return t.viewer.viewer.layers().some((layer: any) => layer.id() === overlayId);
      });
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        const overlayId = t.viewer._annotations[t.overlayAnnotationId].overlays[0].id;
        const layer = t.viewer.viewer.layers().find((layer: any) => layer.id() === overlayId);
        assert.eq(layer.opacity(), 0.5, 'initial overlay opacity');
        t.viewer.setAnnotationOpacity(t.overlayAnnotationId, 0.5);
        assert.eq(layer.opacity(), 0.25, 'reduced overlay opacity');
        t.viewer.setAnnotationOpacity(t.overlayAnnotationId);
        assert.eq(layer.opacity(), 0.5, 'restored overlay opacity');
      });
    });

    await test.step('generates pixelmap layer parameters', async () => {
      const result = await page.evaluate(() => {
        const t = (window as any).__t;
        const overlayMetadata = {
          sizeX: 500,
          sizeY: 500,
          tileWidth: 256,
          tileHeight: 256,
          levels: t.viewer.levels,
        };
        const overlayId = '012345678901234567890123';
        const pixelMapElement = {
          type: 'pixelmap',
          id: '00001111222233334444',
          opacity: 0.5,
          girderId: overlayId,
          boundaries: false,
          values: [0, 1, 0, 1, 0, 1],
          categories: [
            { fillColor: '#000000' },
            { fillColor: '#ffffff' },
          ],
        };
        const pixelmapLayerParams = t.viewer._generateOverlayLayerParams(overlayMetadata, overlayId, pixelMapElement);
        pixelMapElement.boundaries = true;
        const pixelmapLayerParamsWithBoundaries = t.viewer._generateOverlayLayerParams(overlayMetadata, overlayId, pixelMapElement);
        return {
          url: pixelmapLayerParams.url,
          data: pixelmapLayerParams.data,
          dataWithBoundaries: pixelmapLayerParamsWithBoundaries.data,
          overlayId,
        };
      });
      expect(result.url.endsWith(`api/v1/item/${result.overlayId}/tiles/zxy/{z}/{x}/{y}?encoding=PNG`)).toBe(true);
      expect(result.data).toEqual([0, 1, 0, 1, 0, 1]);
      expect(result.dataWithBoundaries).toEqual([0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1]);
    });

    await test.step('mouse over events', async () => {
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.events = { context: {}, mouseon: false, mouseover: false, wrong: [] };
        t.viewer.on('g:mouseOnAnnotation', (element: unknown, annotation: string) => {
          if (annotation !== t.annotationId) { t.events.wrong.push(annotation); }
          t.events.mouseon = true;
        }, t.events.context);
        t.viewer.on('g:mouseOverAnnotation', (element: unknown, annotation: string) => {
          if (annotation !== t.annotationId) { t.events.wrong.push(annotation); }
          t.events.mouseover = true;
        }, t.events.context);
        t.interactor.simulateEvent('mousemove', { map: t.viewer.viewer.gcsToDisplay({ x: 1000, y: 1000 }) });
        t.interactor.simulateEvent('mousemove', { map: t.viewer.viewer.gcsToDisplay({ x: 100, y: 100 }) });
      });
      await page.waitForFunction(() => {
        const t = (window as any).__t;
        return t.events.mouseon && t.events.mouseover;
      });
      const wrong = await page.evaluate(() => {
        const t = (window as any).__t;
        t.viewer.off(null, null, t.events.context);
        return t.events.wrong;
      });
      expect(wrong).toEqual([]);
    });

    await test.step('mouse out events', async () => {
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.events = { context: {}, mouseout: false, mouseoff: false, wrong: [] };
        t.viewer.on('g:mouseOutAnnotation', (element: unknown, annotation: string) => {
          if (annotation !== t.annotationId) { t.events.wrong.push(annotation); }
          t.events.mouseout = true;
        }, t.events.context);
        t.viewer.on('g:mouseOffAnnotation', (element: unknown, annotation: string) => {
          if (annotation !== t.annotationId) { t.events.wrong.push(annotation); }
          t.events.mouseoff = true;
        }, t.events.context);
        t.interactor.simulateEvent('mousemove', { map: t.viewer.viewer.gcsToDisplay({ x: 1000, y: 1000 }) });
      });
      await page.waitForFunction(() => {
        const t = (window as any).__t;
        return t.events.mouseoff && t.events.mouseout;
      });
      const wrong = await page.evaluate(() => {
        const t = (window as any).__t;
        t.viewer.off(null, null, t.events.context);
        return t.events.wrong;
      });
      expect(wrong).toEqual([]);
    });

    await test.step('mouse click events', async () => {
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.events = { context: {}, mouseclick: false, wrong: [] };
        t.viewer.on('g:mouseClickAnnotation', (element: unknown, annotation: string) => {
          if (annotation !== t.annotationId) { t.events.wrong.push(annotation); }
          t.events.mouseclick = true;
        }, t.events.context);
        const pt = t.viewer.viewer.gcsToDisplay({ x: 100, y: 100 });
        t.interactor.simulateEvent('mousedown', { button: 'left', map: pt });
        t.interactor.simulateEvent('mouseup', { button: 'left', map: pt });
      });
      await page.waitForFunction(() => (window as any).__t.events.mouseclick);
      const wrong = await page.evaluate(() => {
        const t = (window as any).__t;
        t.viewer.off(null, null, t.events.context);
        return t.events.wrong;
      });
      expect(wrong).toEqual([]);
    });

    await test.step('fires overlay event', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const eventType = w.geo.event.feature.mouseclick;
        const mockEvent = { event: eventType, data: {} };
        const mockOverlay = t.overlayAnnotation.elements().models[0] || {};
        t.mockLayer = t.viewer.viewer.createLayer('feature');
        t.events = { mouseclick: false };
        t.viewer.on('g:mouseClickAnnotationOverlay', () => {
          t.events.mouseclick = true;
        });
        t.viewer._onMouseFeature(mockEvent, mockOverlay, t.mockLayer);
      });
      await page.waitForFunction(() => (window as any).__t.events.mouseclick);
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.viewer.off('g:mouseClickAnnotationOverlay');
        t.viewer.viewer.deleteLayer(t.mockLayer);
      });
    });

    await test.step('mouse reset events', async () => {
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.events = { context: {}, mousereset: false, wrong: [] };
        t.viewer.on('g:mouseResetAnnotation', (annotation: any) => {
          if (annotation.id !== t.annotationId) { t.events.wrong.push(annotation.id); }
          t.events.mousereset = true;
        }, t.events.context);
        t.annotation.trigger('g:fetched');
      });
      await page.waitForFunction(() => (window as any).__t.events.mousereset);
      const wrong = await page.evaluate(() => {
        const t = (window as any).__t;
        t.viewer.off(null, null, t.events.context);
        t.viewer.viewer.zoom(1);
        return t.events.wrong;
      });
      expect(wrong).toEqual([]);
    });

    await test.step('removeAnnotation', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        t.viewer.removeAnnotation(t.annotation);
        t.viewer.removeAnnotation(t.overlayAnnotation);
        w.__assert.deepEq(t.viewer._annotations, {}, 'annotations after removal');
        w.__assert.eq(t.featureSpy.callCount, 1, '_exit call count');
      });
    });

    await test.step('drawAnnotation without fetching', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const largeImageAnnotation = w.girder.plugins.large_image_annotation;
        t.noFetchModel = new largeImageAnnotation.models.AnnotationModel({
          _id: 'invalid',
          annotation: {
            name: 'no fetch',
            elements: [{
              type: 'rectangle',
              center: [100, 100, 0],
              rotation: 0,
              width: 10,
              height: 10,
            }],
          },
        });
        t.noFetchSpy = w.__spy(t.noFetchModel, 'setView');
        t.viewer.drawAnnotation(t.noFetchModel, { fetch: false });
        t.viewer.viewer.zoom(5);
      });
      await waitForIdlePage(page);
      const callCount = await page.evaluate(() => {
        const t = (window as any).__t;
        t.viewer.viewer.zoom(1);
        return t.noFetchSpy.callCount;
      });
      expect(callCount).toBe(0);
    });

    await test.step('drawRegion', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        t.regionModel = new w.girder.Backbone.Model();
        t.viewer.drawRegion(t.regionModel);
        t.interactor.simulateEvent('mousedown', { button: 'left', map: t.viewer.viewer.gcsToDisplay({ x: 100, y: 100 }) });
        t.interactor.simulateEvent('mousemove', { button: 'left', map: t.viewer.viewer.gcsToDisplay({ x: 115, y: 115 }) });
        t.interactor.simulateEvent('mouseup', { button: 'left', map: t.viewer.viewer.gcsToDisplay({ x: 115, y: 115 }) });
      });
      await page.waitForFunction(() => !!(window as any).__t.regionModel.get('value'));
      const value = await page.evaluate(() => (window as any).__t.regionModel.get('value'));
      expect(value).toEqual([100, 100, 15, 15]);
    });

    /**
     * Start a draw mode, simulate clicks at the given image coordinates, and
     * return the created elements.  Each click is preceded by a mouse move.
     */
    const draw = async (mode: string, points: number[][], extraClicks = 0) => {
      await page.evaluate(({ mode, points, extraClicks }) => {
        const t = (window as any).__t;
        t.created = undefined;
        t.viewer.startDrawMode(mode).then((elements: unknown) => {
          t.created = elements;
          return null;
        });
        points.forEach(([x, y], idx) => {
          const pt = t.viewer.viewer.gcsToDisplay({ x, y });
          if (idx > 0 || mode !== 'point') {
            t.interactor.simulateEvent('mousemove', { button: 'left', map: pt });
          }
          t.interactor.simulateEvent('mousedown', { button: 'left', map: pt });
          t.interactor.simulateEvent('mouseup', { button: 'left', map: pt });
        });
        // Extra clicks at the last point finish polygons and lines.
        const last = t.viewer.viewer.gcsToDisplay({ x: points[points.length - 1][0], y: points[points.length - 1][1] });
        for (let i = 0; i < extraClicks; i += 1) {
          t.interactor.simulateEvent('mousedown', { button: 'left', map: last });
          t.interactor.simulateEvent('mouseup', { button: 'left', map: last });
        }
      }, { mode, points, extraClicks });
      await page.waitForFunction(() => !!(window as any).__t.created);
      return await page.evaluate(() => (window as any).__t.created) as any[];
    };

    const closeTo = (a: number[], b: number[], tol = 6) => {
      expect(a.length).toBe(b.length);
      for (let i = 0; i < a.length; i += 1) {
        expect(a[i]).toBeCloseTo(b[i], tol);
      }
    };

    await test.step('draw point', async () => {
      const elements = await draw('point', [[100, 200]]);
      expect(elements.length).toBe(1);
      expect(elements[0].type).toBe('point');
      closeTo(elements[0].center, [100, 200, 0]);
    });

    await test.step('draw polygon', async () => {
      const elements = await draw('polygon', [[100, 200], [200, 200], [200, 300], [200, 300]], 1);
      expect(elements.length).toBe(1);
      expect(elements[0].type).toBe('polyline');
      expect(elements[0].closed).toBe(true);
      expect(elements[0].points.length).toBe(3);
      // these could be in any order, so sort them
      const points = elements[0].points.sort((a: number[], b: number[]) => {
        if (a[0] !== b[0]) {
          return a[0] < b[0] ? -1 : 1;
        }
        return a[1] < b[1] ? -1 : 1;
      });
      closeTo(points[0], [100, 200, 0]);
      closeTo(points[1], [200, 200, 0]);
      closeTo(points[2], [200, 300, 0]);
    });

    await test.step('draw rectangle', async () => {
      const elements = await draw('rectangle', [[100, 200], [200, 400]]);
      expect(elements.length).toBe(1);
      closeTo(elements[0].center, [150, 300, 0]);
      expect(elements[0].width).toBe(100);
      expect(elements[0].height).toBe(200);
    });

    await test.step('draw ellipse', async () => {
      const elements = await draw('ellipse', [[100, 200], [200, 400]]);
      expect(elements.length).toBe(1);
      closeTo(elements[0].center, [150, 300, 0]);
      expect(elements[0].width).toBe(100);
      expect(elements[0].height).toBe(200);
    });

    await test.step('draw circle', async () => {
      const elements = await draw('circle', [[100, 100], [200, 500]]);
      expect(elements.length).toBe(1);
      closeTo(elements[0].center, [200, 200, 0]);
      expect(elements[0].radius).toBe(100);
    });

    await test.step('draw line', async () => {
      const elements = await draw('line', [[100, 200], [200, 200], [200, 300], [200, 300]], 1);
      expect(elements.length).toBe(1);
      expect(elements[0].type).toBe('polyline');
      expect(elements[0].closed).toBe(false);
      expect(elements[0].points.length).toBe(3);
      closeTo(elements[0].points[0], [100, 200, 0]);
      closeTo(elements[0].points[1], [200, 200, 0]);
      closeTo(elements[0].points[2], [200, 300, 0]);
    });

    const waitForTextEditor = (count: number) =>
      page.waitForFunction((count) => (window as any).__t.$el.find('.g-li-annotation-text-edit').length === count, count);

    await test.step('text elements: draw text', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        t.created = undefined;
        t.triggered = undefined;
        w.girder.events.once('g:annotationCreated', (element: unknown) => {
          t.triggered = element;
        });
        t.viewer.startDrawMode('text', { textStyle: { lineColor: '#ff0000', fontSize: 20, lineWidth: 5 } }).then((elements: unknown) => {
          t.created = elements;
          return null;
        });
        w.__assert.eq(t.viewer.annotationLayer.mode(), 'point', 'draw mode');
        t.clickAt(100, 200);
      });
      await waitForTextEditor(1);
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        const input = t.$el.find('.g-li-annotation-text-edit');
        const pt = t.viewer.viewer.gcsToDisplay({ x: 100, y: 200 });
        assert.eq(t.viewer.annotationLayer.mode(), null, 'draw mode after click');
        assert.eq(t.viewer.annotationLayer.annotations().length, 0, 'annotation count');
        assert.ok(document.activeElement === input[0], 'editor is focused');
        assert.eq(input.val(), '', 'initial text');
        assert.close(parseFloat(input.css('left')), pt.x, 0, 'editor left');
        assert.close(parseFloat(input.css('top')), pt.y, 0, 'editor top');
        assert.eq(input.css('font-size'), '20px', 'font size');
        assert.eq(input.css('line-height'), '25px', 'line height');
        assert.eq(input.css('color'), 'rgb(255, 0, 0)', 'color');
        assert.eq(input.css('background-color'), 'rgba(0, 0, 0, 0)', 'background');
        // tabs and control characters are fixed while typing
        t.typeText('  A\tcomment\u0007\r\non two lines ');
        assert.eq(input.val(), '  A comment\non two lines ', 'typed text');
        assert.eq(input.attr('rows'), '2', 'rows');
        // the editor moves with the map
        const zoom = t.viewer.viewer.zoom();
        t.viewer.viewer.zoom(zoom + 1);
        const pt2 = t.viewer.viewer.gcsToDisplay({ x: 100, y: 200 });
        assert.greater(Math.abs(pt2.x - pt.x) + Math.abs(pt2.y - pt.y), 5, 'editor moved');
        assert.close(parseFloat(input.css('left')), pt2.x, 0, 'editor left after zoom');
        assert.close(parseFloat(input.css('top')), pt2.y, 0, 'editor top after zoom');
        t.viewer.viewer.zoom(zoom);
        // enter adds a line and doesn't finish
        t.key(input, 'Enter');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 1, 'editor after enter');
        assert.eq(t.created, undefined, 'not created after enter');
        t.key(input, 'Enter', true);
      });
      await page.waitForFunction(() => !!(window as any).__t.created);
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 0, 'editor removed');
        assert.eq(t.created.length, 1, 'created count');
        assert.eq(t.created[0].type, 'text', 'created type');
        assert.eq(t.created[0].text, 'A comment\non two lines', 'created text');
        assert.eq(t.created[0].lineColor, '#ff0000', 'created lineColor');
        assert.eq(t.created[0].fontSize, 20, 'created fontSize');
        assert.eq(t.created[0].lineWidth, undefined, 'created lineWidth');
        assert.eq(t.created[0].fillColor, undefined, 'created fillColor');
        assert.match(t.created[0].id, /^[0-9a-f]{24}$/, 'created id');
        assert.closeTo(t.created[0].center, [100, 200, 0], 6, 'created center');
        assert.ok(t.triggered === t.created[0], 'g:annotationCreated triggered');
      });
    });

    await test.step('text elements: draw text finishes when focus is lost', async () => {
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.created = undefined;
        t.viewer.startDrawMode('text', { trigger: false }).then((elements: unknown) => {
          t.created = elements;
          return null;
        });
        t.clickAt(150, 250);
      });
      await waitForTextEditor(1);
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.typeText('Blurred').trigger('blur');
      });
      await page.waitForFunction(() => !!(window as any).__t.created);
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        assert.eq(t.created[0].text, 'Blurred', 'blurred text');
        assert.eq(t.created[0].lineColor, 'rgb(0,0,0)', 'blurred lineColor');
        assert.eq(t.created[0].fontSize, 16, 'blurred fontSize');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 0, 'editor removed');
      });
    });

    await test.step('text elements: empty text is discarded', async () => {
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.created = undefined;
        t.rejected = 0;
        t.drawText = () => {
          t.viewer.startDrawMode('text').then((elements: unknown) => {
            t.created = elements;
            return null;
          }, () => {
            t.rejected += 1;
          });
          t.clickAt(100, 200);
        };
        t.drawText();
      });
      await waitForTextEditor(1);
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.key(t.typeText(' \n\t  '), 'Enter', true);
      });
      await page.waitForFunction(() => (window as any).__t.rejected === 1);
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        w.__assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 0, 'editor removed');
        t.drawText();
      });
      await waitForTextEditor(1);
      await page.evaluate(() => {
        const t = (window as any).__t;
        // escape cancels even if there is text
        t.key(t.typeText('Canceled'), 'Escape');
      });
      await page.waitForFunction(() => (window as any).__t.rejected === 2);
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        w.__assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 0, 'editor removed');
        w.__assert.eq(t.created, undefined, 'nothing created');
      });
    });

    await test.step('text elements: restarting text draw mode abandons text entry', async () => {
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.settled = false;
        t.viewer.startDrawMode('text', { trigger: false }).always(() => {
          t.settled = true;
        });
        t.clickAt(100, 200);
      });
      await waitForTextEditor(1);
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        t.typeText('Abandoned');
        t.viewer.startDrawMode('text', { trigger: false });
        // a new point is placed before the text is typed
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 0, 'editor removed');
        assert.eq(t.viewer.annotationLayer.mode(), 'point', 'draw mode');
        assert.eq(t.settled, false, 'not settled');
        t.viewer.startDrawMode(null);
      });
    });

    await test.step('text elements: starting another draw mode abandons text entry', async () => {
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.settled = false;
        t.viewer.startDrawMode('text').always(() => {
          t.settled = true;
        });
        t.clickAt(100, 200);
      });
      await waitForTextEditor(1);
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        t.typeText('Abandoned');
        t.viewer.startDrawMode('point');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 0, 'editor removed');
        assert.eq(t.settled, false, 'not settled');
        t.viewer.startDrawMode(null);
      });
    });

    await test.step('text elements: startTextEdit and finishTextEdit', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        const results: unknown[] = [];

        const lines: string[] = [];
        for (let i = 0; i < 200; i += 1) {
          const words: string[] = [];
          for (let j = 0; j < 15; j += 1) {
            words.push(`word${i * 15 + j}`);
          }
          lines.push(words.join(' '));
        }
        t.longText = lines.join('\n');

        const record = (name: string) => {
          // done and fail are called synchronously
          return t.viewer.startTextEdit({ center: [100, 100, 0], text: name, fontSize: 12 }).done((text: string) => {
            results.push(['resolved', text]);
          }).fail(() => {
            results.push(['rejected', name]);
          });
        };
        record('first');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').val(), 'first', 'first text');
        // starting a second edit finishes the first
        record('second');
        assert.deepEq(results, [['resolved', 'first']], 'first resolved');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 1, 'one editor');
        t.typeText('changed');
        t.viewer.finishTextEdit();
        assert.deepEq(results[1], ['resolved', 'changed'], 'changed resolved');
        record('third');
        t.viewer.finishTextEdit(false);
        assert.deepEq(results[2], ['rejected', 'third'], 'third rejected');
        record('fourth');
        t.viewer.finishTextEdit(null);
        assert.eq(results.length, 3, 'fourth neither resolved nor rejected');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 0, 'no editor');
        // nothing happens if there is no editor
        t.viewer.finishTextEdit();
        assert.eq(results.length, 3, 'no change without an editor');
        // a comment of a few thousand words can be edited
        record(t.longText);
        assert.eq(t.$el.find('.g-li-annotation-text-edit').val(), t.longText, 'long text');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').attr('rows'), '200', 'long text rows');
        t.typeText(t.longText + '\nand one more line');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').attr('rows'), '201', 'long text rows after edit');
        t.viewer.finishTextEdit();
        assert.deepEq(results[3], ['resolved', t.longText + '\nand one more line'], 'long text resolved');
      });
    });

    await test.step('text elements: the enter key can finish editing', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        const $ = w.girder.$;
        const results: string[] = [];

        const record = (text: string, options?: Record<string, unknown>) => {
          t.viewer.startTextEdit({ center: [100, 100, 0], text }, options).done((text: string) => {
            results.push(text);
          });
          return t.$el.find('.g-li-annotation-text-edit');
        };
        // by default, enter doesn't finish and control-enter does
        let input = record('default');
        t.key(input, 'Enter');
        assert.deepEq(results, [], 'enter does not finish');
        input.trigger($.Event('keydown', { key: 'Enter', shiftKey: true }));
        assert.deepEq(results, [], 'shift-enter does not finish');
        t.key(input, 'Enter', true);
        assert.deepEq(results, ['default'], 'control-enter finishes');
        input = record('explicit', { enterKey: 'newline' });
        t.key(input, 'Enter');
        assert.eq(results.length, 1, 'explicit newline');
        input.trigger($.Event('keydown', { key: 'Enter', metaKey: true }));
        assert.deepEq(results, ['default', 'explicit'], 'meta-enter finishes');
        // when enter finishes, the modified keys add lines
        input = record('first', { enterKey: 'finish' });
        assert.match(input.attr('title'), /^Enter or click elsewhere/, 'title');
        input.trigger($.Event('keydown', { key: 'Enter', shiftKey: true }));
        assert.eq(results.length, 2, 'shift-enter adds a line');
        input[0].setSelectionRange(5, 5);
        t.key(input, 'Enter', true);
        assert.eq(results.length, 2, 'control-enter adds a line');
        assert.eq(input.val(), 'first\n', 'line added');
        assert.eq(input.attr('rows'), '2', 'rows');
        input.val('first\nsecond').trigger('input');
        input[0].setSelectionRange(2, 4);
        input.trigger($.Event('keydown', { key: 'Enter', metaKey: true }));
        assert.eq(input.val(), 'fi\nt\nsecond', 'selection replaced');
        assert.eq(input[0].selectionStart, 3, 'selection start');
        t.key(input, 'Enter');
        assert.deepEq(results, ['default', 'explicit', 'fi\nt\nsecond'], 'enter finishes');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 0, 'no editor');
      });
    });

    await test.step('text elements: move text by dragging and edit it by clicking', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        const $ = w.girder.$;
        const results: unknown[][] = [];
        let handle: any;
        let offset: { left: number, top: number };
        let pt: { x: number, y: number };
        let center: { x: number, y: number };

        const record = (options?: Record<string, unknown>) => {
          t.viewer.startTextEdit({ center: [100, 200, 0], text: 'Movable\ntext', fontSize: 20, lineColor: '#0000ff' }, options).done((text: string, center: number[]) => {
            results.push(['resolved', text, center]);
          }).fail(() => {
            results.push(['rejected']);
          });
          return t.$el.find('.g-li-annotation-text-move');
        };
        const mouse = (target: any, name: string, dx: number, dy: number) => {
          target.trigger($.Event(name, { which: 1, pageX: offset.left + dx, pageY: offset.top + dy }));
        };
        // without the option, the text is edited immediately
        t.viewer.startTextEdit({ center: [100, 200, 0], text: 'Not movable' });
        assert.eq(t.$el.find('.g-li-annotation-text-move').length, 0, 'no handle');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 1, 'editor');
        t.viewer.finishTextEdit(null);

        handle = record({ movable: true });
        assert.eq(handle.length, 1, 'handle');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 0, 'no editor');
        assert.eq(handle.text(), 'Movable\ntext', 'handle text');
        assert.eq(handle.css('font-size'), '20px', 'handle font size');
        assert.eq(handle.css('color'), 'rgb(0, 0, 255)', 'handle color');
        assert.eq(handle.css('white-space'), 'pre', 'handle white-space');
        assert.ok(document.activeElement === handle[0], 'handle focused');
        pt = t.viewer.viewer.gcsToDisplay({ x: 100, y: 200 });
        assert.close(parseFloat(handle.css('left')), pt.x, 0, 'handle left');
        assert.close(parseFloat(handle.css('top')), pt.y, 0, 'handle top');
        offset = handle.offset();
        // drag it
        mouse(handle, 'mousedown', 5, 5);
        mouse($(document), 'mousemove', 6, 6);
        // a tiny movement doesn't move it
        assert.close(parseFloat(handle.css('left')), pt.x, 0, 'tiny move');
        mouse($(document), 'mousemove', 35, 25);
        assert.close(parseFloat(handle.css('left')), pt.x + 30, 0, 'dragged left');
        assert.close(parseFloat(handle.css('top')), pt.y + 20, 0, 'dragged top');
        mouse($(document), 'mouseup', 35, 25);
        // it is still there and wasn't switched to editing
        assert.eq(t.$el.find('.g-li-annotation-text-move').length, 1, 'handle after drag');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 0, 'no editor after drag');
        assert.deepEq(results, [], 'no results after drag');
        // moving the mouse without the button down does nothing
        mouse($(document), 'mousemove', 100, 100);
        assert.close(parseFloat(handle.css('left')), pt.x + 30, 0, 'no move without button');
        // it can be dragged again, and releasing over the text works
        offset = handle.offset();
        mouse(handle, 'mousedown', 5, 5);
        mouse($(document), 'mousemove', 15, -5);
        mouse(handle, 'mouseup', 15, -5);
        assert.close(parseFloat(handle.css('left')), pt.x + 40, 0, 'second drag left');
        assert.close(parseFloat(handle.css('top')), pt.y + 10, 0, 'second drag top');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 0, 'no editor after second drag');
        center = t.viewer.viewer.displayToGcs({ x: pt.x + 40, y: pt.y + 10 });
        // finishing without editing reports the new location
        t.viewer.finishTextEdit();
        assert.eq(results.length, 1, 'one result');
        assert.eq(results[0][1], 'Movable\ntext', 'moved text');
        assert.closeTo(results[0][2] as number[], [center.x, center.y, 0], 3, 'moved center');
        assert.eq(t.$el.find('.g-li-annotation-text-move').length, 0, 'handle removed');

        // a click switches to editing
        handle = record({ movable: true });
        offset = handle.offset();
        mouse(handle, 'mousedown', 5, 5);
        mouse(handle, 'mouseup', 5, 5);
        assert.eq(t.$el.find('.g-li-annotation-text-move').length, 0, 'handle removed on click');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 1, 'editor on click');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').val(), 'Movable\ntext', 'editor text');
        assert.ok(document.activeElement === t.$el.find('.g-li-annotation-text-edit')[0], 'editor focused');
        assert.eq(results.length, 1, 'still one result');
        t.key(t.typeText('Edited'), 'Enter', true);
        assert.deepEq(results[1], ['resolved', 'Edited', [100, 200, 0]], 'edited result');

        // drag and then click to edit; both changes are reported
        handle = record({ movable: true, enterKey: 'finish' });
        offset = handle.offset();
        mouse(handle, 'mousedown', 5, 5);
        mouse($(document), 'mousemove', 35, 25);
        mouse($(document), 'mouseup', 35, 25);
        offset = handle.offset();
        mouse(handle, 'mousedown', 5, 5);
        mouse($(document), 'mouseup', 5, 5);
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 1, 'editor after drag and click');
        pt = t.viewer.viewer.gcsToDisplay({ x: 100, y: 200 });
        assert.close(parseFloat(t.$el.find('.g-li-annotation-text-edit').css('left')), pt.x + 30, 0, 'editor left');
        t.key(t.typeText('Moved and edited'), 'Enter');
        center = t.viewer.viewer.displayToGcs({ x: pt.x + 30, y: pt.y + 20 });
        assert.eq(results[2][1], 'Moved and edited', 'moved and edited text');
        assert.closeTo(results[2][2] as number[], [center.x, center.y, 0], 3, 'moved and edited center');

        // enter switches to editing and escape cancels a move
        handle = record({ movable: true });
        t.key(handle, 'Enter');
        assert.eq(t.$el.find('.g-li-annotation-text-edit').length, 1, 'editor on enter');
        t.viewer.finishTextEdit(null);
        handle = record({ movable: true });
        offset = handle.offset();
        mouse(handle, 'mousedown', 5, 5);
        mouse($(document), 'mousemove', 35, 25);
        mouse($(document), 'mouseup', 35, 25);
        t.key(handle, 'Escape');
        assert.deepEq(results[3], ['rejected'], 'escape rejects');
        assert.eq(t.$el.find('.g-li-annotation-text-move').length, 0, 'handle removed on escape');
        // losing focus finishes
        handle = record({ movable: true });
        handle.trigger('blur');
        assert.deepEq(results[4], ['resolved', 'Movable\ntext', [100, 200, 0]], 'blur resolves');
        assert.eq(results.length, 5, 'five results');
      });
    });

    await test.step('text elements: draw text elements', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const largeImageAnnotation = w.girder.plugins.large_image_annotation;
        // place the text so that it doesn't overlap on screen
        t.center1 = t.viewer.viewer.displayToGcs({ x: 100, y: 80 });
        t.center2 = t.viewer.viewer.displayToGcs({ x: 250, y: 200 });
        t.textModel = new largeImageAnnotation.models.AnnotationModel({
          _id: 'textannotation',
          annotation: {
            name: 'text',
            elements: [{
              id: 'a00000000000000000000001',
              type: 'text',
              center: [t.center1.x, t.center1.y, 0],
              text: 'A comment',
            }, {
              id: 'a00000000000000000000002',
              type: 'text',
              center: [t.center2.x, t.center2.y, 0],
              text: 'long first line\nshort',
              lineColor: 'rgba(255, 0, 0, 0.5)',
              fontSize: 24,
            }, {
              id: 'a00000000000000000000004',
              type: 'rectangle',
              center: [300, 300, 0],
              rotation: 0,
              width: 10,
              height: 10,
            }],
          },
        });
        w.__assert.eq(t.viewer.textLayer, null, 'no text layer yet');
        t.viewer.drawAnnotation(t.textModel, { fetch: false });
      });
      await waitForIdlePage(page);
      await page.waitForFunction(() => {
        const t = (window as any).__t;
        return t.viewer._annotations[t.textModel.id] && t.viewer._annotations[t.textModel.id].features.length === 2;
      });
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        const features = t.viewer._annotations[t.textModel.id].features;
        let text = features.filter((feature: any) => feature.featureType === 'text');
        assert.ok(t.viewer.textLayer !== null, 'text layer');
        assert.eq(t.viewer.textLayer.features().length, 1, 'text layer features');
        // drawn annotations are above the text
        assert.greater(t.viewer.annotationLayer.zIndex(), t.viewer.textLayer.zIndex(), 'z index');
        assert.eq(text.length, 1, 'text feature count');
        assert.eq(features.length, 2, 'feature count');
        text = text[0];
        assert.eq(text.data().length, 2, 'text data count');
        assert.eq(text.style.get('text')(text.data()[1], 1), 'long first line\nshort', 'text style');
        assert.eq(text.style.get('font')(text.data()[0], 0), '16px/20px sans-serif', 'font 0');
        assert.eq(text.style.get('font')(text.data()[1], 1), '24px/30px sans-serif', 'font 1');
        assert.eq(text.style('color')(text.data()[0], 0), '#000000', 'color 0');
        assert.eq(text.style('color')(text.data()[1], 1), '#ff0000', 'color 1');
        assert.eq(text.style.get('textOpacity')(text.data()[0], 0), 1, 'opacity 0');
        assert.eq(text.style.get('textOpacity')(text.data()[1], 1), 0.5, 'opacity 1');
        assert.deepEq(text.position()(text.data()[1], 1), { x: t.center2.x, y: t.center2.y }, 'position');
        // redrawing replaces the feature
        t.viewer.drawAnnotation(t.textModel, { fetch: false });
      });
      await waitForIdlePage(page);
      const count = await page.evaluate(() => (window as any).__t.viewer.textLayer.features().length);
      expect(count).toBe(1);
    });

    await test.step('text elements: draw a long comment', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const largeImageAnnotation = w.girder.plugins.large_image_annotation;
        t.longModel = new largeImageAnnotation.models.AnnotationModel({
          _id: 'longtextannotation',
          annotation: {
            name: 'long text',
            elements: [{
              id: 'b00000000000000000000001',
              type: 'text',
              center: [100, 300, 0],
              text: t.longText,
            }],
          },
        });
        t.viewer.drawAnnotation(t.longModel, { fetch: false });
      });
      await waitForIdlePage(page);
      await page.waitForFunction(() => {
        const t = (window as any).__t;
        return t.viewer._annotations[t.longModel.id] && t.viewer._annotations[t.longModel.id].features.length >= 1;
      });
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        const text = t.viewer._annotations[t.longModel.id].features[0];
        assert.eq(t.viewer.textLayer.features().length, 2, 'text layer features');
        assert.eq(text.featureType, 'text', 'feature type');
        assert.eq(text.style.get('text')(text.data()[0], 0), t.longText, 'long text');
        // the text is drawn and can be found
        t.viewer.viewer.draw();
        const found = text.pointSearch({ x: 100, y: 300 });
        assert.eq(found.found.length, 1, 'found count');
        assert.eq(found.found[0].id, 'b00000000000000000000001', 'found id');
        t.viewer.removeAnnotation(t.longModel);
        assert.eq(t.viewer.textLayer.features().length, 1, 'text layer features after removal');
      });
    });

    await test.step('text elements: text opacity, highlighting, and hiding', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        const text = t.viewer.textLayer.features()[0];
        const opacities = () => text.data().map((d: unknown, i: number) => text.style.get('textOpacity')(d, i));
        t.viewer.highlightAnnotation(t.textModel.id, 'a00000000000000000000001');
        assert.deepEq(opacities(), [1, 0.5 * 0.33], 'highlight element');
        t.viewer.highlightAnnotation(t.textModel.id);
        assert.deepEq(opacities(), [1, 0.5], 'highlight annotation');
        t.viewer.highlightAnnotation('otherannotation');
        assert.deepEq(opacities(), [0.33, 0.5 * 0.33], 'highlight other');
        t.viewer.highlightAnnotation();
        assert.deepEq(opacities(), [1, 0.5], 'reset highlight');
        t.viewer.hideAnnotation(t.textModel.id, 'a00000000000000000000002');
        assert.deepEq(opacities(), [1, 0], 'hide element');
        t.viewer.hideAnnotation();
        assert.deepEq(opacities(), [1, 0.5], 'reset hide');
        t.viewer.setGlobalAnnotationOpacity(0.5);
        assert.eq(t.viewer.textLayer.opacity(), 0.5, 'global opacity');
        assert.deepEq(opacities(), [1, 0.5], 'opacities with global opacity');
        t.viewer.setAnnotationOpacity(t.textModel.id, 0.25);
        assert.eq(t.viewer.textLayer.opacity(), 0.5, 'global opacity unchanged');
        assert.deepEq(opacities(), [0.5, 0.25], 'annotation opacity');
        t.viewer.setAnnotationOpacity(t.textModel.id);
        t.viewer.setGlobalAnnotationOpacity(1);
        assert.eq(t.viewer.textLayer.opacity(), 1, 'global opacity reset');
        assert.deepEq(opacities(), [1, 0.5], 'opacities reset');
      });
    });

    await test.step('text elements: text mouse events', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        const over: string[] = [];
        const out: string[] = [];
        const clicked: string[] = [];
        const context = {};

        t.viewer.on('g:mouseOverAnnotation', (element: any, annotation: string) => {
          assert.eq(annotation, t.textModel.id, 'mouse over annotation');
          over.push(element.id);
        }, context);
        t.viewer.on('g:mouseOutAnnotation', (element: any) => {
          out.push(element.id);
        }, context);
        t.viewer.on('g:mouseClickAnnotation', (element: any) => {
          clicked.push(element.id);
        }, context);

        const moveTo = (x: number, y: number, dx?: number, dy?: number) => {
          let pt = t.viewer.viewer.gcsToDisplay({ x, y });
          pt = { x: pt.x + (dx || 0), y: pt.y + (dy || 0) };
          t.interactor.simulateEvent('mousemove', { map: pt });
          return pt;
        };
        t.interactor.simulateEvent('mousemove', { map: { x: 390, y: 10 } });
        moveTo(t.center1.x, t.center1.y);
        assert.deepEq(over, ['a00000000000000000000001'], 'over first');
        moveTo(t.center1.x, t.center1.y, 0, 30);
        assert.deepEq(out, ['a00000000000000000000001'], 'out first');
        // each line of multiline text is checked separately.  The second
        // line is shorter than the first.  The available fonts vary between
        // test environments, so measure the lines to pick a horizontal offset
        // that is within the first line but outside the second.
        const measure = (text: string) => {
          const ctx = document.createElement('canvas').getContext('2d') as CanvasRenderingContext2D;
          ctx.font = '24px/30px sans-serif';
          return ctx.measureText(text).width;
        };
        const dx = -(measure('long first line') / 2 - 8);
        assert.greater(-dx, measure('short') / 2 + 4, 'first line is wider than the second');
        moveTo(t.center2.x, t.center2.y, dx, -15);
        assert.deepEq(over, ['a00000000000000000000001', 'a00000000000000000000002'], 'over second');
        moveTo(t.center2.x, t.center2.y, dx, 15);
        assert.deepEq(out, ['a00000000000000000000001', 'a00000000000000000000002'], 'out second');
        const pt = moveTo(t.center2.x, t.center2.y, 0, 15);
        assert.eq(over.length, 3, 'over count');
        t.interactor.simulateEvent('mousedown', { button: 'left', map: pt });
        t.interactor.simulateEvent('mouseup', { button: 'left', map: pt });
        assert.deepEq(clicked, ['a00000000000000000000002'], 'clicked');
        // hidden text doesn't get events
        t.interactor.simulateEvent('mousemove', { map: { x: 390, y: 10 } });
        t.viewer.hideAnnotation(t.textModel.id, 'a00000000000000000000002');
        moveTo(t.center2.x, t.center2.y, 0, 15);
        assert.eq(over.length, 3, 'over count with hidden text');
        t.viewer.hideAnnotation();
        t.interactor.simulateEvent('mousemove', { map: { x: 390, y: 10 } });
        t.viewer.off(null, null, context);
      });
    });

    await test.step('text elements: remove text elements', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        t.viewer.removeAnnotation(t.textModel);
        w.__assert.eq(t.viewer.textLayer.features().length, 0, 'text layer features');
        w.__assert.eq(t.viewer._annotations[t.textModel.id], undefined, 'annotation record');
      });
    });

    await test.step('global annotation opacity', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        let opacity = null;
        const opacityFunction = t.viewer.featureLayer.opacity;
        t.viewer.featureLayer.opacity = (_opacity: number) => {
          opacity = _opacity;
        };
        try {
          t.viewer.setGlobalAnnotationOpacity(0.5);
          w.__assert.eq(opacity, 0.5, 'global opacity');
        } finally {
          t.viewer.featureLayer.opacity = opacityFunction;
        }
      });
    });

    await test.step('global annotation fill opacity', async () => {
      const id = await createAnnotation(page, {
        name: 'annotation1',
        elements: [{
          id: '111111111111111111111111',
          type: 'rectangle',
          center: [200, 200, 0],
          width: 400,
          height: 400,
          rotation: 0,
          fillColor: '#000',
        }],
      });
      await page.evaluate((id) => {
        const w = window as any;
        const t = w.__t;
        const largeImageAnnotation = w.girder.plugins.large_image_annotation;
        t.fillAnnotation = new largeImageAnnotation.models.AnnotationModel({ _id: id });
        t.viewer.drawAnnotation(t.fillAnnotation);
      }, id);
      await waitForIdlePage(page);
      await page.waitForFunction(() => {
        const t = (window as any).__t;
        return t.viewer._annotations[t.fillAnnotation.id] && t.viewer._annotations[t.fillAnnotation.id].features.length >= 1;
      });
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        const polygonFeature = t.viewer.viewer.layers()[1].features()[2];
        assert.eq(polygonFeature.style.get('fillOpacity')(null, 0, null, 0), 1, 'initial fill opacity');
        t.viewer.setGlobalAnnotationFillOpacity(0.5);
        assert.eq(polygonFeature.style.get('fillOpacity')(null, 0, null, 0), 0.5, 'reduced fill opacity');
        t.viewer.setGlobalAnnotationFillOpacity(1);
        assert.eq(polygonFeature.style.get('fillOpacity')(null, 0, null, 0), 1, 'restored fill opacity');
      });
    });

    const element11 = '111111111111111111111111';
    const element12 = '222222222222222222222222';
    const element21 = '333333333333333333333333';
    const element22 = '444444444444444444444444';

    await test.step('highlight and hide annotations: generate test annotations', async () => {
      const id1 = await createAnnotation(page, {
        name: 'annotation1',
        elements: [{
          id: element11,
          type: 'rectangle',
          center: [200, 200, 0],
          width: 400,
          height: 400,
          rotation: 0,
          fillColor: 'rgba(0, 0, 0, 0.5)',
        }, {
          id: element12,
          type: 'rectangle',
          center: [300, 300, 0],
          width: 100,
          height: 100,
          rotation: 0,
          fillColor: 'rgba(0, 0, 0, 0.5)',
        }],
      });
      const id2 = await createAnnotation(page, {
        name: 'annotation2',
        elements: [{
          id: element21,
          type: 'rectangle',
          center: [200, 200, 0],
          width: 400,
          height: 400,
          rotation: 0,
          fillColor: 'rgba(0, 0, 0, 0.5)',
        }, {
          id: element22,
          type: 'point',
          center: [300, 300, 0],
          fillColor: 'rgba(0, 0, 0, 0.5)',
        }],
      });
      await page.evaluate(({ id1, id2 }) => {
        const w = window as any;
        const t = w.__t;
        const largeImageAnnotation = w.girder.plugins.large_image_annotation;
        t.annotation1 = new largeImageAnnotation.models.AnnotationModel({ _id: id1 });
        t.annotation2 = new largeImageAnnotation.models.AnnotationModel({ _id: id2 });
        t.viewer.drawAnnotation(t.annotation1);
        t.viewer.drawAnnotation(t.annotation2);
      }, { id1, id2 });
      await waitForIdlePage(page);
      await page.waitForFunction(() => {
        const t = (window as any).__t;
        return [t.annotation1.id, t.annotation2.id].every((id) => t.viewer._annotations[id] && t.viewer._annotations[id].features.length >= 1);
      });
    });

    await test.step('highlight a full annotation', async () => {
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.viewer.highlightAnnotation(t.annotation1.id);
        t.checkFeatureOpacity(t.annotation1.id, 0.5, 1);
        t.checkFeatureOpacity(t.annotation2.id, 0.5 * 0.33, 0.33);
      });
    });

    await test.step('highlight a single element', async () => {
      await page.evaluate((element21) => {
        const t = (window as any).__t;
        t.viewer.highlightAnnotation(t.annotation2.id, element21);
        t.checkFeatureOpacity(t.annotation1.id, 0.5 * 0.33, 0.33);
        t.checkFeatureOpacity(t.annotation2.id, 0.5 * 0.33, 0.33, (data: any) => data.id !== element21);
        t.checkFeatureOpacity(t.annotation2.id, 0.5, 1, (data: any) => data.id === element21);
      }, element21);
    });

    await test.step('reset opacities', async () => {
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.viewer.highlightAnnotation();
        t.checkFeatureOpacity(t.annotation1.id, 0.5, 1);
        t.checkFeatureOpacity(t.annotation2.id, 0.5, 1);
      });
    });

    await test.step('handles custom unselected opacity multiplier', async () => {
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.viewer.setUnselectedOpacityMultiplier(0.5);
        t.viewer.highlightAnnotation(t.annotation1.id);
        t.checkFeatureOpacity(t.annotation1.id, 0.5, 1);
        t.checkFeatureOpacity(t.annotation2.id, 0.5 * 0.5, 0.5);
        t.viewer.highlightAnnotation();
        t.viewer.setUnselectedOpacityMultiplier();
        t.checkFeatureOpacity(t.annotation1.id, 0.5, 1);
        t.checkFeatureOpacity(t.annotation2.id, 0.5, 1);
      });
    });

    await test.step('hide an element', async () => {
      await page.evaluate((element21) => {
        const t = (window as any).__t;
        t.viewer.hideAnnotation(t.annotation2.id, element21);
        t.checkFeatureOpacity(t.annotation1.id, 0.5, 1);
        t.checkFeatureOpacity(t.annotation2.id, 0.5, 1, (data: any) => data.id !== element21);
        t.checkFeatureOpacity(t.annotation2.id, 0, 0, (data: any) => data.id === element21);
      }, element21);
    });

    await test.step('reset opacities after hiding', async () => {
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.viewer.hideAnnotation();
        t.checkFeatureOpacity(t.annotation1.id, 0.5, 1);
        t.checkFeatureOpacity(t.annotation2.id, 0.5, 1);
      });
    });

    await test.step('set annotation opacity', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        t.viewer.setGlobalAnnotationOpacity(0.5);
        t.viewer.setAnnotationOpacity(t.annotation1.id, 0.25);
        assert.eq(t.viewer.featureLayer.opacity(), 0.5, 'feature layer opacity');
        t.checkFeatureOpacity(t.annotation1.id, 0.25, 0.5);
        t.checkFeatureOpacity(t.annotation2.id, 0.5, 1);

        t.viewer.setAnnotationOpacity(t.annotation1.id, 1);
        assert.eq(t.viewer.featureLayer.opacity(), 1, 'feature layer opacity at 1');
        t.checkFeatureOpacity(t.annotation1.id, 0.5, 1);
        t.checkFeatureOpacity(t.annotation2.id, 0.25, 0.5);

        t.viewer.setAnnotationOpacity(t.annotation1.id);
        assert.eq(t.viewer.featureLayer.opacity(), 0.5, 'feature layer opacity reset');
        t.checkFeatureOpacity(t.annotation1.id, 0.5, 1);
        t.checkFeatureOpacity(t.annotation2.id, 0.5, 1);
      });
    });

    await test.step('heatmap opacity', async () => {
      const id = await createAnnotation(page, {
        name: 'heatmap',
        elements: [{
          type: 'heatmap',
          points: [[100, 100, 0, 1], [200, 200, 0, 2]],
        }],
      });
      await page.evaluate((id) => {
        const w = window as any;
        const t = w.__t;
        const largeImageAnnotation = w.girder.plugins.large_image_annotation;
        t.heatmapAnnotation = new largeImageAnnotation.models.AnnotationModel({ _id: id });
        t.viewer.drawAnnotation(t.heatmapAnnotation);
      }, id);
      await page.waitForFunction(() => {
        const t = (window as any).__t;
        return (t.viewer._annotations[t.heatmapAnnotation.id] || { features: [] }).features.length;
      });
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        const layer = t.viewer._annotations[t.heatmapAnnotation.id].features[0].layer();
        t.viewer.setGlobalAnnotationOpacity(0.5);
        assert.eq(layer.opacity(), 0.5, 'heatmap global opacity');
        t.viewer.setAnnotationOpacity(t.heatmapAnnotation.id, 0.25);
        assert.eq(layer.opacity(), 0.25, 'heatmap annotation opacity');
        t.viewer.setAnnotationOpacity(t.heatmapAnnotation.id);
        assert.eq(layer.opacity(), 0.5, 'heatmap opacity reset');
        t.viewer.removeAnnotation(t.heatmapAnnotation);
      });
    });

    await test.step('large annotations: generate several sizes of annotations', async () => {
      const ids: string[] = [];
      for (const i of [0, 1, 2]) {
        const elements = new Array(Math.pow(10, i + 1)).fill(0).map((_elem, idx) => ({
          type: 'rectangle',
          center: [0.2 + (idx % 100) * 0.1, 0.2 + (Math.floor(idx / 100)) * 0.1, 0],
          width: 0.12 + (idx % 40) * 0.01,
          height: 0.12 + (idx % 51) * 0.01,
          rotation: 0,
          fillColor: 'rgba(0, 0, 0, 0.5)',
        }));
        ids.push(await createAnnotation(page, { name: `annotation${i}`, elements }));
      }
      await page.evaluate((ids) => {
        const w = window as any;
        const t = w.__t;
        const largeImageAnnotation = w.girder.plugins.large_image_annotation;
        t.largeAnnotations = ids.map((id) => new largeImageAnnotation.models.AnnotationModel({
          _id: id,
          maxDetails: 50,
          minElements: 1,
          maxCentroids: 500,
        }));
        t.largeAnnotations.forEach((annot: unknown) => t.viewer.drawAnnotation(annot));
      }, ids);
      await waitForIdlePage(page);
      await page.waitForFunction(() => {
        const t = (window as any).__t;
        return t.largeAnnotations.every((annot: any) => t.viewer._annotations[annot.id] && t.viewer._annotations[annot.id].features.length >= 1);
      });
    });

    await test.step('check that annotations are using centroids when appropriate', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        const annotations = t.largeAnnotations;
        assert.eq(annotations[0]._centroids, undefined, 'small annotation has no centroids');
        assert.ok(annotations[1]._centroids !== undefined, 'medium annotation has centroids');
        assert.eq(annotations[1]._centroids.partial, undefined, 'medium annotation is not partial');
        assert.ok(annotations[2]._centroids !== undefined, 'large annotation has centroids');
        assert.ok(annotations[2]._centroids.partial !== undefined, 'large annotation is partial');
        t.viewer.viewer.zoom(t.viewer.viewer.zoom() + 1);
        assert.ok(annotations[1]._lastZoom !== undefined, 'last zoom');
      });
    });

    await test.step('set opacity of an annotation using centroids', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const assert = w.__assert;
        const annotation = t.largeAnnotations[1];
        const feature = t.viewer._annotations[annotation.id].features.find((feature: any) => feature._centroidFeature);
        const fillOpacity = feature.style.get('fillOpacity');
        t.viewer.setGlobalAnnotationOpacity(0.5);
        const opacity = fillOpacity(feature.data()[0], 0);
        t.viewer.setAnnotationOpacity(annotation.id, 0.25);
        assert.eq(fillOpacity(feature.data()[0], 0), opacity * 0.5, 'centroid opacity');
        t.viewer.setAnnotationOpacity(annotation.id);
        assert.eq(fillOpacity(feature.data()[0], 0), opacity, 'centroid opacity reset');
      });
    });

    await test.step('destroy the viewer', async () => {
      await page.evaluate(() => {
        const t = (window as any).__t;
        t.viewer.destroy();
      });
      await expect(page.locator('.geojs-layer')).toHaveCount(0);
    });

    await test.step('scale', async () => {
      await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const GeojsViewer = w.girder.plugins.large_image.views.imageViewerWidget.geojs;
        t.viewer = new GeojsViewer({
          el: t.$el,
          itemId: t.itemId,
          parentView: null,
          scale: { position: { bottom: 20, right: 10 }, scale: 0.0005 },
        });
      });
      await page.waitForFunction(() => {
        const t = (window as any).__t;
        return document.querySelectorAll('.geojs-layer.active').length >= 1 && t.viewer.scaleWidget;
      });
      const isScaleWidget = await page.evaluate(() => {
        const w = window as any;
        const t = w.__t;
        const result = t.viewer.scaleWidget instanceof w.geo.gui.scaleWidget;
        t.viewer.destroy();
        return result;
      });
      expect(isScaleWidget).toBe(true);
    });
  });
});
