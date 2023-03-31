import path from 'path'
import * as url from 'url'

import MiniCssExtractPlugin from 'mini-css-extract-plugin'

const __dirname = url.fileURLToPath(new URL('.', import.meta.url))


export default {
    entry: './html/kg/app/index.js',
    output: {
        filename: 'bundle.js',
        path: path.resolve(__dirname, 'html/kg'),
        library: {
            type: 'module',
        },
    },
    experiments: {
        outputModule: true,
    },
    module: {
        rules: [
            {
                test: /\.css$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    'css-loader',
                ],
            },
        ],
    },
    plugins: [
        new MiniCssExtractPlugin({
            filename: 'bundle.css',
        }),
    ],
    mode: 'production',
    // mode: 'development',
}