const path = require('path');

const webpack = require('webpack');

const CopyWebpackPlugin = require('copy-webpack-plugin');

module.exports = function (config) {
    config.plugins.push(
        new CopyWebpackPlugin([{
            from: require.resolve('geojs'),
            to: path.join(config.output.path, 'extra', 'geojs.js'),
            toType: 'file'
        }, {
            from: path.join(path.resolve(__dirname), 'node_modules', 'slideatlas-viewer', 'dist'),
            to: path.join(config.output.path, 'extra', 'slideatlas')
        }, {
            from: path.join(path.resolve(__dirname), 'node_modules', 'sinon', 'pkg', 'sinon.js'),
            to: path.join(config.output.path, 'extra', 'sinon.js')
        }])
    );
    config.plugins.push(
        new webpack.DefinePlugin({
            BUILD_TIMESTAMP: Date.now()
        })
    );
    return config;
};
