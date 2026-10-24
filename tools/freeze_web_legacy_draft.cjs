/* Materialize an authentic PR7 full v1 draft without running a browser/engine. */
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto');
const root=path.join(__dirname,'..'),window={},context=vm.createContext({window}),sources={};
for(const file of ['catalog.js','settings.js']) {const p=path.join(root,'docs/research/pybert-signal-chain-ui',file),content=fs.readFileSync(p);sources[path.relative(root,p)]=crypto.createHash('sha256').update(content).digest('hex');vm.runInContext(content.toString('utf8'),context);}
const values=JSON.parse(JSON.stringify(window.PYBERT_SETTINGS.defaults));values.bit_rate=25;values.vod=1.25;
const output=path.join(root,'docs/webui/issue5/fixtures/pr7-schema1-full.json');
if(fs.existsSync(output))throw new Error('Refusing to overwrite frozen legacy draft');
fs.writeFileSync(output,JSON.stringify({schema:1,commit:window.PYBERT_CATALOG.commit,values},null,2),'utf8');
fs.writeFileSync(path.join(root,'docs/webui/issue5/fixtures/pr7-schema1-source.json'),JSON.stringify({sources,changes:{bit_rate:25,vod:1.25},schema:1},null,2),'utf8');
console.log(JSON.stringify({draft:output,field_count:Object.keys(values).length,source_commit:window.PYBERT_CATALOG.commit}));
