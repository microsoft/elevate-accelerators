const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require("html-webpack-plugin");
const Webpack = require("webpack");
const path = require("path");
const fs = require("fs");

function listDefinitionFiles(root) {
    const walk = directory => fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
        if (entry.name.startsWith('.')) return [];
        const fullPath = path.join(directory, entry.name);
        if (entry.isDirectory()) return walk(fullPath);
        return [path.relative(root, fullPath).replaceAll('\\', '/')];
    });
    return walk(root).sort();
}

const reportsRoot = path.resolve(__dirname, '../../../power-bi');
const semanticModelRoot = path.join(reportsRoot, 'EducationAnalytics.SemanticModel');
const reportRoot = path.join(reportsRoot, 'EducationAnalytics.Report');
const reportingAssets = {
    semanticModel: listDefinitionFiles(semanticModelRoot),
    report: listDefinitionFiles(reportRoot),
};

class ReportingAssetManifestPlugin {
    apply(compiler) {
        compiler.hooks.thisCompilation.tap('ReportingAssetManifestPlugin', compilation => {
            compilation.contextDependencies.add(semanticModelRoot);
            compilation.contextDependencies.add(reportRoot);
            compilation.hooks.processAssets.tap(
                {
                    name: 'ReportingAssetManifestPlugin',
                    stage: compiler.webpack.Compilation.PROCESS_ASSETS_STAGE_ADDITIONAL,
                },
                () => {
                    compilation.emitAsset(
                        'assets/deployment/reporting/manifest.json',
                        new compiler.webpack.sources.RawSource(JSON.stringify(reportingAssets)),
                    );
                },
            );
        });
    }
}


console.log('*******************     Workload Configuration    *******************');
console.log('process.env.WORKLOAD_NAME: ' + process.env.WORKLOAD_NAME);
console.log('process.env.ITEM_NAMES: ' + process.env.ITEM_NAMES);
console.log('process.env.WORKLOAD_VERSION: ' + process.env.WORKLOAD_VERSION);
console.log('process.env.LOG_LEVEL: ' + process.env.LOG_LEVEL);
console.log('*********************************************************************');


module.exports = {
    mode: "production",
    entry: "./app/index.ts",
    output: {
        filename: "bundle.[fullhash].js",
        path: path.resolve(__dirname, "dist"),
        publicPath: '/',
    },
    plugins: [
        new CleanWebpackPlugin(),
        new Webpack.DefinePlugin({
            "process.env.WORKLOAD_NAME": JSON.stringify(process.env.WORKLOAD_NAME),
            "process.env.ITEM_NAMES": JSON.stringify(process.env.ITEM_NAMES),
            "process.env.WORKLOAD_VERSION": JSON.stringify(process.env.WORKLOAD_VERSION),
            "process.env.LOG_LEVEL": JSON.stringify(process.env.LOG_LEVEL),
            "process.env.ENABLE_PLAYGROUND": JSON.stringify(process.env.ENABLE_PLAYGROUND || 'false'),
            "process.env.ENABLE_STANDALONE_PREVIEW": JSON.stringify(process.env.ENABLE_STANDALONE_PREVIEW || 'false'),
        }),
        new Webpack.ProvidePlugin({
            process: 'process/browser.js',
        }),
        new HtmlWebpackPlugin({
            template: "./app/index.html",
        }),
        new ReportingAssetManifestPlugin(),
        new CopyWebpackPlugin({
            patterns: [
                {
                    context: './app/assets/',
                    from: 'locales/**/*',
                    to: './assets',
                },
                {
                    from: './app/assets/fabric-icon.png',
                    to: './assets/fabric-icon.png',
                },
                {
                    context: './app/assets/icons',
                    from: '*.svg',
                    to: './assets/icons/[name][ext]',
                },
                {
                    from: './app/web.config',
                    to: './web.config',
                },
                {
                    from: './Manifest/assets/images/Education_Icon.svg',
                    to: './assets/education-icon.svg',
                },
                {
                    context: '../../notebooks',
                    from: '*.ipynb',
                    to: './assets/deployment/notebooks/[name][ext]',
                },
                {
                    from: '../../pipelines/EDU_BR_GD_Processing.DataPipeline/pipeline-content.json',
                    to: './assets/deployment/pipelines/EDU_BR_GD_Processing.json',
                },
                {
                    from: '../../../../sample-data/manifest.json',
                    to: './assets/deployment/sample-data/manifest.json',
                },
                ...['PowerSchool', 'Canvas', 'Moodle', 'NWEA'].map(source => ({
                    context: `../../../../sample-data/${source}`,
                    from: '*.csv',
                    to: `./assets/deployment/sample-data/${source}/[name][ext]`,
                })),
                ...reportingAssets.semanticModel.map(relativePath => ({
                    from: path.join(semanticModelRoot, relativePath),
                    to: `./assets/deployment/reporting/semantic-model/${relativePath}`,
                })),
                ...reportingAssets.report.map(relativePath => ({
                    from: path.join(reportRoot, relativePath),
                    to: `./assets/deployment/reporting/report/${relativePath}`,
                })),
            ]
        }),
    ],
    resolve: {
        modules: [__dirname, "node_modules"],
        extensions: [".*", ".js", ".jsx", ".tsx", ".ts"],
        fullySpecified: false,
        alias: {
            'process/browser': require.resolve('process/browser.js')
        }
    },
    module: {
        rules: [
            {
                test: /\.tsx?$/,
                exclude: /node_modules/,
                loader: "ts-loader",
            },
            {
                test: /\.s[ac]ss$/i,
                use: ["style-loader", "css-loader", "sass-loader"],
            },
            {
                test: /\.(png|jpg|jpeg|svg)$/i,
                type: 'asset/resource'
            },
            {
                test: /\.m?js/,
                resolve: {
                    fullySpecified: false
                }
            }
        ],
    }
};