const path = require('path');

const webpack = require('webpack');

const CopyWebpackPlugin = require('copy-webpack-plugin');
const {VueLoaderPlugin} = require('vue-loader');

module.exports = function (config) {
    config.plugins.push(
        new CopyWebpackPlugin([{
            from: require.resolve('geojs/geo.lean.min.js'),
            to: path.join(config.output.path, 'extra', 'geojs.js'),
            toType: 'file'
        }, {
            from: require.resolve('sinon/pkg/sinon.js'),
            to: path.join(config.output.path, 'extra', 'sinon.js')
        }])
    );
    config.plugins.push(
        new webpack.DefinePlugin({
            BUILD_TIMESTAMP: Date.now()
        })
    );
    config.module.rules.push({
        resource: {
            test: /\.vue$/
        },
        use: [
            require.resolve('vue-loader')
        ]
    });
    config.resolve = {
        alias: {
            vue: process.env.NODE_ENV === 'production' ? 'vue/dist/vue.min.js' : 'vue/dist/vue.js'
        }
    };
    config.plugins.push(new VueLoaderPlugin());
    return config;
};
