const glob = require('glob')
const {ManhattanManifestPlugin} = require('manhattan-manifest-plugin')
const path = require('path')
const S3Plugin = require('webpack-s3-plugin')
const webpack = require('webpack')


module.exports = (env) => {

    // -- Env --

    env.server = process.argv[1].indexOf('webpack-dev-server') >= 0


    // -- Settings --

    const hash = {
        css: '[hash].',
        images: '[hash].',
        js: '[chunkhash].'
    }

    let manifestPlugin = new ManhattanManifestPlugin()

    const plugins = []

    let minimizeCSS = false
    let publicPath = '/'
    let serverPort = 5998
    let watch = false

    if (env.email) {

        watch = true

        // Hash
        hash.css = ''
        hash.images = ''
        hash.js = ''

        // Manifest
        manifestPlugin = new ManhattanManifestPlugin({
            presets: {'__live__': `https://h51.io:${serverPort}`},
            stripHash: (filepath) => { return null }
        })

    } else if (env.server) {

        publicPath = `http://h51.local:${serverPort}/`

        // Hash
        hash.css = ''
        hash.images = ''
        hash.js = ''

        // Manifest
        manifestPlugin = new ManhattanManifestPlugin({
            presets: {'__live__': `http://h51.local:${serverPort}`},
            stripHash: (filepath) => { return null }
        })

    } else if (env.staging || env.production) {

        // Minimize options
        minimizeCSS = true

        // Public path
        publicPath = ''

        // Plugins
        const s3Plugin = new S3Plugin({
            exclude: /emails\/.*\.css$/,
            s3Options: {
                accessKeyId: '',
                secretAccessKey: '',
                region: ''
            },
            s3UploadOptions: {
                Bucket: '',
                CacheControl: 'max-age=31536000, no-transform, public'
            }
        })
        plugins.push(s3Plugin)

    }

    // Add manifest plugin
    plugins.push(manifestPlugin)

    // -- Config --

    return {
        entry: function() {
            return {

                'manage': [
                    './scripts/manage.js',
                    './styles/manage.scss'
                ],

                '_emails': [
                    './styles/emails/manage.scss'
                ],

                '_assets':
                    glob.sync('./images/**/*\.+(gif|jpg|png|svg)').concat(
                        glob.sync('./sounds/**/*\.+(mp3)')
                    )
            }
        },

        output: {
            publicPath: publicPath,
            path: path.resolve(__dirname, 'www'),
            filename: `[name].${hash.js}js`
        },

        watch: watch,

        module: {
            rules: [

                // CSS
                {
                    test: /\.scss$/,
                    exclude: /styles\/emails/,
                    use: [
                        `file-loader?name=[name].${hash.css}css`,
                        'extract-loader',
                        {
                            loader: 'css-loader',
                            options: {
                                importLoaders: 2
                            }
                        }, {
                            loader: 'postcss-loader',
                            options: {
                                ident: 'postcss',
                                plugins: (loader) => {

                                    const postcssPlugins = [
                                        require('autoprefixer')({
                                            'overrideBrowserslist': [
                                                'defaults',
                                                'not IE 11',
                                                'not IE_Mob 11'
                                            ]
                                        })
                                    ]

                                    if (minimizeCSS) {
                                        postcssPlugins.push(
                                            require('cssnano')({
                                                preset: 'default'
                                            })
                                        )
                                    }

                                    return postcssPlugins
                                }
                            }
                        },
                        {loader: 'sass-loader'}
                    ]
                },

                // CSS for emails
                {
                    test: /.scss$/,
                    include: /styles\/emails/,
                    loaders: [
                        'file-loader?name=../emails/[name].css',
                        'extract-loader',
                        'css-loader',
                        'sass-loader'
                    ]
                },

                // JS
                {
                    test: /\.js$/,
                    loader: 'babel-loader',
                    query: {
                        presets: ['@babel/preset-env']
                    }
                },

                // Images / Sounds
                {
                    test: /\.(gif|jpg|png|svg|woff)$/,
                    loader: 'url-loader',
                    options: {
                        name: `[path][name].${hash.images}[ext]`,
                        limit: 0
                    }
                },

                // -- Pre --

                // JS lint
                {
                    enforce: 'pre',
                    test: /\.js$/,
                    loader: 'eslint-loader',
                    exclude: /node_modules/
                }
            ]
        },

        plugins: plugins,

        stats: {
            colors: true
        },

        devServer: {
            contentBase: path.resolve(__dirname, 'www'),
            headers: {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'X-Requested-With, content-type, Authorization'
            },
            inline: true,
            port: serverPort,
            disableHostCheck: true,
            host: '0.0.0.0'
        }
    }
}
