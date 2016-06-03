/* global require */
var fs = require('fs');
var d3 = require('d3');
var _ = require('underscore');
var tinycolor = require('tinycolor2');

function transform(bbox) {
    var x = d3.scale.linear()
        .domain([-50, 50])
        .range([bbox.left, bbox.left + bbox.width]);
    var y = d3.scale.linear()
        .domain([-50, 50])
        .range([bbox.top, bbox.top + bbox.height]);
    function t(pt) {
        return [x(pt[0]), y(pt[1]), 0];
    }
    t.s = d3.scale.linear()
        .range([0, bbox.width / 100]);
    return t;
}

function arrow(start, end, t, props) {
    props = _.defaults(props || {}, {
        type: 'arrow',
        points: [
            t(start),
            t(end)
        ]
    });
    return props
}

function arrows(t) {
    var N = 12;
    var inner = 15;
    var outer = 45;
    var color = d3.scale.category20();
    return _.range(N)
        .map(function (i) {
            var theta = 2 * Math.PI * i / N;
            var sin = Math.sin(theta);
            var cos = Math.cos(theta);
            var start = [outer * cos, outer * sin];
            var end = [inner * cos, inner * sin];
            var props = {
                lineColor: color(i),
                lineWidth: 1.5
            };

            return arrow(start, end, t, props);
        });
}


function circles(t) {
    var N = 24;
    var fill = d3.scale.category20();
    var stroke = d3.scale.category20b();
    return _.range(N)
        .map(function (i) {
            var theta = 2 * Math.PI * i / N;
            var r = i * 45 / N;
            var x = r * Math.cos(theta);
            var y = r * Math.sin(theta);
            var c = tinycolor(fill(i));
            c.setAlpha(i / N);
            return {
                type: 'circle',
                fillColor: c.toRgbString(),
                lineColor: stroke(i),
                lineWidth: 2,
                center: t([x, y]),
                radius: t.s((N - i) * 25 / N)
            }
        });
}

function ellipses(t) {
    var N = 6;
    var eps = 0.25;
    var c = tinycolor('steelblue');

    return _.range(N)
        .map(function (i) {
            var theta = Math.PI * i / N;
            c.setAlpha(1 / N);
            return {
                type: 'ellipse',
                center: t([0, 0]),
                width: t.s(eps * 80),
                height: t.s(80),
                rotation: theta,
                fillColor: c.toRgbString(),
                lineWidth: 2,
                lineColor: 'rgb(0,0,0)'
            };
        });
}

function points(t) {
    var v = _.range(11)
        .map(function (i) {
            return {
                type: 'point',
                center: t([0, (i - 5) * 9])
            };
        });
    var h = _.range(11)
        .map(function (i) {
            return {
                type: 'point',
                center: t([(i - 5) * 9, 0])
            };
        });
    return _.flatten([v, h]);
}

function polylines(t) {
    var N = 100;
    var sin = _.range(N).map(function (i) {
        var x = 90 * (-45 + i) / N;
        var y = 15 * Math.sin(Math.PI * x / 10);
        return t([x, y - 15]);
    });
    var polar = _.range(N).map(function (i) {
        var theta = 2 * Math.PI * i / N;
        var r = 30 * theta * (2 * Math.PI - theta) / (Math.PI * Math.PI);
        return t([
            r * Math.cos(-Math.PI / 2 + theta),
            r * Math.sin(-Math.PI / 2 + theta) + 15
        ]);
    });

    return [{
        type: 'polyline',
        points: sin,
        closed: false,
        lineWidth: 2,
        lineColor: 'firebrick'
    }, {
        type: 'polyline',
        points: polar,
        closed: true,
        fillColor: 'rgba(0, 0, 255, 0.5)'
    }];
}

function rectangles(t) {
    var x = [-50, -20, 10, 25, 40, 50];
    var y = [-50, -30, 0, 20, 30, 50];
    var pad = 3;
    var r = [];
    var line = d3.scale.category10();
    var fill = function (i) {
        var color = tinycolor(line(i));
        color.setAlpha(0.5);
        return color.toRgbString();
    };

    _.range(x.length - 1).forEach(function (i) {
        _.range(y.length - 1).forEach(function (j) {
            var cx = (x[i] + x[i + 1]) / 2;
            var cy = (y[j] + y[j + 1]) / 2;
            r.push({
                type: 'rectangle',
                center: t([cx, cy]),
                width: t.s(x[i + 1] - x[i] - pad),
                height: t.s(y[j + 1] - y[j] - pad),
                fillColor: fill(i),
                lineColor: line(j),
                lineWidth: 2,
                rotation: 0.5 * (0.5 - Math.random())
            });
        });
    });
    return r;
}

function grids(t) {
    var c = tinycolor('yellow');
    c.setAlpha(0.25);
    return [{
        type: 'rectanglegrid',
        center: t([0, 0]),
        width: t.s(70),
        height: t.s(50),
        rotation: 30 * Math.PI / 180,
        widthSubdivisions: 8,
        heightSubdivisions: 6,
        fillColor: c.toRgbString(),
        lineWidth: 1.5
    }];
}

function write_json(name, elements) {
    var obj = {
        name: name,
        elements: elements
    };
    fs.writeFileSync(name + '.json', JSON.stringify(obj, null, 2));
}

var bbox = {
    left: 300,
    top: 0,
    width: 300,
    height: 300
};

var t = transform(bbox);
write_json('arrows', arrows(t));

bbox.left = 600;
t = transform(bbox);
write_json('circles', circles(t));

bbox.left = 900;
t = transform(bbox);
write_json('ellipses', ellipses(t));

bbox.left = 0;
bbox.top = 300;
t = transform(bbox);
write_json('points', points(t));

bbox.left = 300;
t = transform(bbox);
write_json('polylines', polylines(t));

bbox.left = 600;
t = transform(bbox);
write_json('rectangles', rectangles(t));

bbox.left = 900;
t = transform(bbox);
write_json('grids', grids(t));
