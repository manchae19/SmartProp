import fs from 'node:fs';import path from 'node:path';
// Reviewed public files only. Add a filename here when the team adds a new public asset.
export const publicFiles=[
 'background.mp4','favicon.svg','icons.svg','vite.svg',
 "images/home/banner.png",
 "media/projects/sun-ponte.jpg",
 "media/projects/the-filmore.jpg",
 "media/projects/fpt-plaza-3.jpg",
 "media/projects/sun-symphony.jpg",
 "media/projects/sunneva-island.jpg",
 "media/projects/sun-cosmo.jpg"
];
export function approvedFiles(directory){if(!directory||!fs.existsSync(directory))return [];return publicFiles.filter(name=>{const target=path.join(directory,name);if(!fs.existsSync(target))return false;const stat=fs.lstatSync(target);return stat.isFile()&&!stat.isSymbolicLink()})}
export function approvedPublicAssets(){let config;return {name:'smartprop-approved-public-assets',config:()=>({build:{copyPublicDir:false}}),configResolved:value=>config=value,configureServer(server){server.middlewares.use((req,res,next)=>{let pathname;try{pathname=decodeURIComponent((req.url||'').split('?')[0])}catch{res.statusCode=400;res.end();return}if(/\.exe(?:$|[\/])/i.test(pathname)){res.statusCode=404;res.end();return}next()})},writeBundle(options){if(!config.publicDir)return;const output=path.resolve(options.dir||path.resolve(config.root,config.build.outDir));if(output===config.root||output===config.publicDir)throw Error('Unsafe public asset output');for(const name of approvedFiles(config.publicDir)){const target=path.join(output,name);if(!target.startsWith(output+path.sep))throw Error('Invalid public asset path');fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(path.join(config.publicDir,name),target,fs.constants.COPYFILE_EXCL)}}}}
