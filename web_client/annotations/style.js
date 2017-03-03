import _ from 'underscore';

const props = [
    'fillColor',
    'lineColor',
    'lineWidth',
    'label'
];

export default function style(json) {
    return _.pick(json, ...props);
}
