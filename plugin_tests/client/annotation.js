_.each([
    '/plugins/large_image/node_modules/sinon/pkg/sinon.js',
    '/plugins/large_image/web_client/js/ext/tinycolor.js'
], function (src) {
    $('<script/>', {src: src}).appendTo('head');
});

girderTest.addCoveredScripts([
    '/plugins/large_image/web_client/js/annotation/0init.js',
    '/plugins/large_image/web_client/js/annotation/model.js',
    '/plugins/large_image/web_client/js/annotation/element.js',
    '/plugins/large_image/web_client/js/annotation/annotation.js',
    '/plugins/large_image/web_client/js/annotation/layer.js',
    '/plugins/large_image/web_client/js/annotation/viewport.js'
]);

function expectColor(color1, color2) {
    expect(tinycolor(color1).toHexString())
        .toEqual(tinycolor(color2).toHexString());
}

describe('annotation rendering', function () {
    var canvas, elements, viewport;
    beforeEach(function () {
        viewport = new girder.annotation.Viewport({
            width: 800,
            height: 600
        });

        // replace x/y scales to avoid problems with numerical
        // precision in the position assertions.
        viewport.x = d3.scale.identity();
        viewport.y = d3.scale.identity();

        elements = girder.annotation.elements;
        canvas = d3.select('body')
            .append('div')
            .attr('class', 'test-element')
            .style('width', '1000px')
            .style('height', '800px')
            .append('svg')
            .attr('id', 'test-canvas')
            .attr('width', '800')
            .attr('height', '600');
    });
    afterEach(function () {
        $('.test-element').remove();
    });

    describe('Element', function () {
        it('abstract render method throws', function () {
            var model = new girder.annotation.Model({
                type: 'circle',
                center: [300, 300, 0],
                radius: 100,
                fillColor: 'rgba(0, 0, 0, 0.5)'
            });
            var render = new girder.annotation.Element({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render;

            expect(render).toThrow();
        });
    });

    describe('circle', function () {
        it('minimal', function () {
            var model = new girder.annotation.Model({
                type: 'circle',
                center: [300, 300, 0],
                radius: 100,
                fillColor: 'rgba(0, 0, 0, 0.5)'
            });
            new elements.circle({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            var n = canvas.select('circle');
            expect(n.size()).toBe(1);
            expect(parseFloat(n.attr('cx'))).toBe(300);
            expect(parseFloat(n.attr('cy'))).toBe(300);
            expect(parseFloat(n.attr('r'))).toBe(100);
            expectColor(n.style('fill'), '#000000');
            expect(parseFloat(n.style('fill-opacity'))).toBe(0.5);
            expect(n.style('stroke')).toBe('none');
        });

        it('stroked', function () {
            var model = new girder.annotation.Model({
                type: 'circle',
                center: [200, 300, 0],
                radius: 50,
                fillColor: 'rgba(255, 0, 0, 0.5)',
                lineWidth: 1,
                lineColor: 'rgba(0, 255, 0, 0.75)'
            });
            new elements.circle({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            var n = canvas.select('circle');
            expect(n.size()).toBe(1);
            expect(parseFloat(n.attr('cx'))).toBe(200);
            expect(parseFloat(n.attr('cy'))).toBe(300);
            expect(parseFloat(n.attr('r'))).toBe(50);
            expectColor(n.style('fill'), '#ff0000');
            expect(parseFloat(n.style('fill-opacity'))).toBe(0.5);
            expectColor(n.style('stroke'), '#00ff00');
            expect(parseFloat(n.style('stroke-width')), 1);
            expect(parseFloat(n.style('stroke-opacity'))).toBe(0.75);
        });
    });

    describe('ellipse', function () {
        it('minimal', function () {
            var model = new girder.annotation.Model({
                type: 'ellipse',
                center: [300, 300, 0],
                width: 75,
                height: 150,
                rotation: 0.5,
                fillColor: 'rgba(0, 0, 0, 0.5)'
            });
            new elements.ellipse({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            var n = canvas.select('ellipse');
            expect(n.size()).toBe(1);
            expect(parseFloat(n.attr('cx'))).toBe(300);
            expect(parseFloat(n.attr('cy'))).toBe(300);
            expect(parseFloat(n.attr('rx'))).toBe(75 / 2);
            expect(parseFloat(n.attr('ry'))).toBe(150 / 2);
            expectColor(n.style('fill'), '#000000');
            expect(parseFloat(n.style('fill-opacity'))).toBe(0.5);
            expect(n.style('stroke')).toBe('none');
        });

        it('stroked', function () {
            var model = new girder.annotation.Model({
                type: 'ellipse',
                center: [200, 300, 0],
                width: 50,
                height: 75,
                rotation: 0,
                fillColor: 'rgba(255, 0, 0, 0.5)',
                lineWidth: 2,
                lineColor: 'rgba(0, 255, 0, 0.75)'
            });
            new elements.ellipse({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            var n = canvas.select('ellipse');
            expect(n.size()).toBe(1);
            expect(parseFloat(n.attr('cx'))).toBe(200);
            expect(parseFloat(n.attr('cy'))).toBe(300);
            expect(parseFloat(n.attr('rx'))).toBe(50 / 2);
            expect(parseFloat(n.attr('ry'))).toBe(75 / 2);
            expectColor(n.style('fill'), '#ff0000');
            expect(parseFloat(n.style('fill-opacity'))).toBe(0.5);
            expectColor(n.style('stroke'), '#00ff00');
            expect(parseFloat(n.style('stroke-width'))).toBe(2);
            expect(parseFloat(n.style('stroke-opacity'))).toBe(0.75);
        });
    });

    describe('rectangle', function () {
        it('minimal', function () {
            var model = new girder.annotation.Model({
                type: 'rectangle',
                center: [300, 300, 0],
                width: 100,
                height: 150,
                rotation: 0.5,
                fillColor: 'rgba(0, 0, 0, 0.5)'
            });
            new elements.rectangle({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            var n = canvas.select('rect');
            expect(n.size()).toBe(1);
            expect(parseFloat(n.attr('x'))).toBe(250);
            expect(parseFloat(n.attr('y'))).toBe(225);
            expect(parseFloat(n.attr('width'))).toBe(100);
            expect(parseFloat(n.attr('height'))).toBe(150);
            expectColor(n.style('fill'), '#000000');
            expect(parseFloat(n.style('fill-opacity'))).toBe(0.5);
            expect(n.style('stroke')).toBe('none');
        });

        it('stroked', function () {
            var model = new girder.annotation.Model({
                type: 'rectangle',
                center: [200, 300, 0],
                width: 50,
                height: 100,
                rotation: 0.5,
                fillColor: 'rgba(255, 0, 0, 0.5)',
                lineWidth: 2,
                lineColor: 'rgba(0, 255, 0, 0.75)'
            });
            new elements.rectangle({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            var n = canvas.select('rect');
            expect(n.size()).toBe(1);
            expect(parseFloat(n.attr('x'))).toBe(175);
            expect(parseFloat(n.attr('y'))).toBe(250);
            expect(parseFloat(n.attr('width'))).toBe(50);
            expect(parseFloat(n.attr('height'))).toBe(100);
            expectColor(n.style('fill'), '#ff0000');
            expect(parseFloat(n.style('fill-opacity'))).toBe(0.5);
            expectColor(n.style('stroke'), '#00ff00');
            expect(parseFloat(n.style('stroke-width'))).toBe(2);
            expect(parseFloat(n.style('stroke-opacity'))).toBe(0.75);
        });
    });

    describe('point', function () {
        it('minimal', function () {
            var model = new girder.annotation.Model({
                type: 'point',
                center: [300, 200, 0]
            });
            new elements.point({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            var n = canvas.select('circle');
            expect(n.size()).toBe(1);
            expect(parseFloat(n.attr('cx'))).toBe(300);
            expect(parseFloat(n.attr('cy'))).toBe(200);
            expect(n.style('stroke')).toBe('none');
        });
    });

    describe('arrow', function () {
        it('minimal', function () {
            var model = new girder.annotation.Model({
                type: 'arrow',
                points: [[100, 50, 0], [200, 100, 0]]
            });
            new elements.arrow({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            var n = canvas.select('line');
            expect(n.size()).toBe(1);
            expect(parseFloat(n.attr('x1'))).toBe(100);
            expect(parseFloat(n.attr('x2'))).toBe(200);
            expect(parseFloat(n.attr('y1'))).toBe(50);
            expect(parseFloat(n.attr('y2'))).toBe(100);
            expect(n.attr('marker-end')).toBe('url(#h-arrow-head)');
        });
    });

    describe('polyline', function () {
        it('open', function () {
            var model = new girder.annotation.Model({
                type: 'polyline',
                points: [
                    [300, 300, 0],
                    [300, 200, 0],
                    [200, 300, 0]
                ],
                lineWidth: 2,
                lineColor: 'rgba(0, 0, 255, 0.8)'
            });
            new elements.polyline({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            var n = canvas.select('path');
            expect(n.size()).toBe(1);
            expect(n.attr('d')).toBe('M300,300L300,200L200,300');
            expectColor(n.style('stroke'), '#0000ff');
            expect(parseFloat(n.style('stroke-width'))).toBe(2);
            expect(n.style('fill')).toBe('none');
        });

        it('closed', function () {
            var model = new girder.annotation.Model({
                type: 'polyline',
                points: [
                    [300, 300, 0],
                    [300, 200, 0],
                    [200, 300, 0]
                ],
                lineWidth: 0.5,
                lineColor: 'rgba(0, 0, 255, 0.8)',
                closed: true
            });
            new elements.polyline({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            var n = canvas.select('path');
            expect(n.size()).toBe(1);
            expect(n.attr('d')).toBe('M300,300L300,200L200,300Z');
            expectColor(n.style('stroke'), '#0000ff');
            expect(parseFloat(n.style('stroke-width'))).toBe(0.5);
            expect(n.style('fill')).toBe('none');
        });

        it('filled', function () {
            var model = new girder.annotation.Model({
                type: 'polyline',
                points: [
                    [300, 300, 0],
                    [300, 200, 0],
                    [200, 300, 0]
                ],
                lineWidth: 0.5,
                lineColor: 'rgba(0, 0, 255, 0.8)',
                closed: true,
                fillColor: 'rgba(255, 0, 0, 0.25)'
            });
            new elements.polyline({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            var n = canvas.select('path');
            expect(n.size()).toBe(1);
            expect(n.attr('d')).toBe('M300,300L300,200L200,300Z');
            expectColor(n.style('stroke'), '#0000ff');
            expect(parseFloat(n.style('stroke-width'))).toBe(0.5);
            expectColor(n.style('fill'), '#ff0000');
            expect(parseFloat(n.style('fill-opacity'))).toBe(0.25);
        });
    });

    describe('rectanglegrid', function () {
        it('minimal', function () {
            var model = new girder.annotation.Model({
                type: 'rectanglegrid',
                center: [400, 300, 0],
                width: 200,
                height: 150,
                rotation: 0,
                widthSubdivisions: 4,
                heightSubdivisions: 3
            });
            new elements.rectanglegrid({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            expect(canvas.node().getBBox())
                .toEqual({x: 300, y: 225, width: 200, height: 150});

            var n = canvas.selectAll('line.h-horizontal');
            expect(n.size()).toBe(4);

            n = canvas.selectAll('line.h-vertical');
            expect(n.size()).toBe(5);

            expect(canvas.select('rect').style('fill')).toBe('none');
            expectColor(canvas.select('line').style('stroke'), '#000');
        });

        it('rotated', function () {
            var model = new girder.annotation.Model({
                type: 'rectanglegrid',
                center: [400, 300, 0],
                width: 200,
                height: 200,
                rotation: Math.PI / 4,
                widthSubdivisions: 4,
                heightSubdivisions: 3
            });
            new elements.rectanglegrid({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            var bbox = canvas.node().getBBox();
            expect(Math.abs(bbox.x - 400 + 200 / Math.sqrt(2))).toBeLessThan(1e-4);
            expect(Math.abs(bbox.y - 300 + 200 / Math.sqrt(2))).toBeLessThan(1e-4);
            expect(Math.abs(bbox.width - 400 / Math.sqrt(2))).toBeLessThan(1e-4);
            expect(Math.abs(bbox.height - 400 / Math.sqrt(2))).toBeLessThan(1e-4);
        });

        it('styled', function () {
            var model = new girder.annotation.Model({
                type: 'rectanglegrid',
                center: [400, 300, 0],
                width: 200,
                height: 200,
                rotation: Math.PI / 4,
                widthSubdivisions: 4,
                heightSubdivisions: 3,
                lineWidth: 2,
                lineColor: 'rgba(255, 0, 0, 0.75)',
                fillColor: 'rgba(0, 255, 0, 0.25)'
            });
            new elements.rectanglegrid({
                viewport: viewport,
                el: canvas.node(),
                model: model
            }).render();

            var count = 0;
            canvas.selectAll('line')
                .each(function () {
                    var d = d3.select(this);
                    expectColor(d.style('stroke'), '#f00');
                    expect(+d.style('stroke-opacity')).toBe(0.75);
                    expect(d.style('stroke-width')).toBe('2px');
                    count += 1;
                });
            expect(count).toBe(9);

            var rect = canvas.select('rect');
            expectColor(rect.style('fill'), '#0f0');
            expect(+rect.style('fill-opacity')).toBe(0.25);
            expect(rect.style('stroke')).toBe('none');
        });
    });

    describe('svg layer', function () {
        var Layer;
        beforeEach(function () {
            Layer = girder.annotation.Layer;
        });
        it('auto sizing', function () {
            var $el = $('.test-element');
            var layer = new Layer({
                el: canvas.node()
            }).render();

            expect(layer.$el.width()).toBe($el.width());
            expect(layer.$el.height()).toBe($el.height());
        });
        it('resizing', function () {
            var layer = new Layer({
                size: {width: 500, height: 500},
                el: canvas.node()
            }).render();

            expect(layer.$el.width()).toBe(500);
            expect(layer.$el.height()).toBe(500);

            layer.size({width: 700, height: 400});
            expect(layer.$el.width()).toBe(700);
            expect(layer.$el.height()).toBe(400);

            expect(layer.size()).toEqual({
                width: 700,
                height: 400
            });
        });
    });

    describe('annotation view', function () {
        var Annotation, Model;
        beforeEach(function () {
            Annotation = girder.annotation.Annotation;
            Model = girder.annotation.Model;
            sinon.stub(console, 'warn');
        });
        afterEach(function () {
            console.warn.restore();
        });
        it('render', function () {
            var view = new Annotation({
                viewport: viewport,
                el: canvas.node(),
                name: 'Test annotation',
                description: 'This is just a test',
                elements: [{
                    type: 'circle',
                    center: [300, 300, 0],
                    radius: 100,
                    fillColor: '#000'
                }, {
                    type: 'point',
                    center: [100, 100, 0]
                }]
            });
            view.render();
            expect(canvas.selectAll('g').size()).toBe(2);

            var count = 0;
            canvas.selectAll('g').each(function () {
                count += 1;
                var d = d3.select(this);
                expect(d.select('circle').size()).toBe(1);
            });

            expect(count).toBe(2);
        });
        it('bad element type', function () {
            var view = new Annotation({
                viewport: viewport,
                el: canvas.node(),
                name: 'Test annotation',
                description: 'This is just a test'
            });

            view.addOne(new Model({
                id: 'badelement',
                type: 'not-an-element',
                center: [300, 300, 0]
            }));

            sinon.assert.calledWith(
                console.warn,
                'Unknown annotation type "not-an-element"'
            );

            expect(canvas.selectAll('#badelement').size()).toBe(0);
        });
        it('addOne', function () {
            var view = new Annotation({
                viewport: viewport,
                el: canvas.node(),
                name: 'Test annotation',
                description: 'This is just a test'
            });

            view.addOne(new Model({
                id: 'a-point',
                type: 'point',
                center: [300, 200, 0]
            }));

            expect(canvas.selectAll('#a-point').size()).toBe(1);
            expect(canvas.selectAll('g').size()).toBe(1);
        });
        it('removeOne', function () {
            var view = new Annotation({
                viewport: viewport,
                el: canvas.node(),
                name: 'Test annotation',
                description: 'This is just a test',
                elements: [{
                    id: 'a-point',
                    type: 'point',
                    center: [300, 200, 0]
                }]
            });
            view.render();

            expect(canvas.selectAll('#a-point').size()).toBe(1);
            expect(canvas.selectAll('g').size()).toBe(1);

            view.removeOne(view.collection.models[0]);
            expect(canvas.selectAll('#a-point').size()).toBe(0);
            expect(canvas.selectAll('g').size()).toBe(0);
        });
    });
});

describe('viewport', function () {
    var Viewport;
    beforeEach(function () {
        Viewport = girder.annotation.Viewport;
    });
    it('scale=1', function () {
        var vp = new Viewport({
            scale: 1,
            left: 0,
            top: 0,
            width: 100,
            height: 50
        });

        expect(vp.viewport()).toEqual({
            left: 0,
            right: 100,
            top: 0,
            bottom: 50
        });

        expect(vp.x(0)).toBe(0);
        expect(vp.x(50)).toBe(50);

        expect(vp.y(0)).toBe(0);
        expect(vp.y(50)).toBe(50);

        expect(vp.imageScale(10)).toBe(10);
        expect(vp.pixelScale(5)).toBe(5);
    });
    it('scale=2', function () {
        var vp = new Viewport({
            scale: 2,
            left: 0,
            top: 0,
            width: 100,
            height: 50
        });

        expect(vp.viewport()).toEqual({
            left: 0,
            right: 200,
            top: 0,
            bottom: 100
        });

        expect(vp.x(0)).toBe(0);
        expect(vp.x(50)).toBe(25);

        expect(vp.y(0)).toBe(0);
        expect(vp.y(50)).toBe(25);

        expect(vp.imageScale(10)).toBe(20);
        expect(vp.pixelScale(5)).toBe(5);
    });
    it('translate=(100,200)', function () {
        var vp = new Viewport({
            scale: 1,
            left: 100,
            top: 200,
            width: 100,
            height: 50
        });

        expect(vp.viewport()).toEqual({
            left: 100,
            right: 200,
            top: 200,
            bottom: 250
        });

        expect(vp.x(100)).toBe(0);
        expect(vp.x(150)).toBe(50);

        expect(vp.y(200)).toBe(0);
        expect(vp.y(250)).toBe(50);

        expect(vp.imageScale(10)).toBe(10);
        expect(vp.pixelScale(5)).toBe(5);
    });
    it('translate=(100,200) scale=2', function () {
        var vp = new Viewport({
            scale: 2,
            left: 100,
            top: 200,
            width: 100,
            height: 50
        });

        expect(vp.viewport()).toEqual({
            left: 100,
            right: 300,
            top: 200,
            bottom: 300
        });

        expect(vp.x(100)).toBe(0);
        expect(vp.x(150)).toBe(25);

        expect(vp.y(200)).toBe(0);
        expect(vp.y(250)).toBe(25);

        expect(vp.imageScale(10)).toBe(20);
        expect(vp.pixelScale(5)).toBe(5);
    });
    it('events', function () {
        var translate = sinon.spy();
        var scale = sinon.spy();
        var vp = new Viewport({
            scale: 1,
            left: 0,
            top: 0,
            width: 100,
            height: 50
        });

        vp.on('translate', translate);
        vp.on('scale', scale);

        vp.set('left', 10);
        expect(translate.callCount).toBe(1);
        expect(scale.callCount).toBe(0);

        vp.set('top', 10);
        expect(translate.callCount).toBe(2);
        expect(scale.callCount).toBe(0);

        vp.set('width', 200);
        expect(translate.callCount).toBe(3);
        expect(scale.callCount).toBe(0);

        vp.set('height', 100);
        expect(translate.callCount).toBe(4);
        expect(scale.callCount).toBe(0);

        translate = sinon.spy();
        vp.on('translate', translate);

        vp.set('scale', 10);
        expect(translate.callCount).toBe(1);
        expect(scale.callCount).toBe(1);
        sinon.assert.callOrder(scale, translate);

        expect(vp.viewport()).toEqual({
            left: -890,
            top: -440,
            right: 1110,
            bottom: 560
        });
    });
    it('center', function () {
        var vp = new Viewport({
            scale: 1,
            left: 0,
            top: 0,
            width: 100,
            height: 50
        });

        expect(vp.center()).toEqual({
            x: 50,
            y: 25
        });

        vp.center({
            x: 100,
            y: 30
        });

        expect(vp.center()).toEqual({
            x: 100,
            y: 30
        });

        expect(vp.get('left')).toBe(50);
        expect(vp.get('top')).toBe(5);
    });
    it('zoom', function () {
        var vp = new Viewport({
            scale: 1,
            left: 0,
            top: 0,
            width: 100,
            height: 50
        });

        expect(vp.zoom()).toBe(0);
        vp.zoom(-2);
        expect(vp.zoom()).toBe(-2);
        expect(vp.get('scale')).toBe(0.25);
    });
});
