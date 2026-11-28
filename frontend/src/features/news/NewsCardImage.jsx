import {useState} from 'react';
import {newsCardMedia} from './newsEditorialCovers.js';

function NewsPlaceholder() {
  return <div className="news-card-visual news-image-fallback" role="img" aria-label="Ảnh minh họa chưa khả dụng"><span>Ảnh minh họa chưa khả dụng</span></div>;
}

export default function NewsCardImage({article}) {
  const {url,illustration}=newsCardMedia(article);
  const [failed,setFailed]=useState(null);
  const identity=JSON.stringify([article.id,url]);
  if(!url||failed===identity)return <NewsPlaceholder article={article}/>;
  return <div className="news-card-visual news-card-photo"><img key={identity}
    src={url} alt={illustration?'Ảnh minh họa: '+illustration.caption:''} width="960" height="540" loading="lazy" decoding="async"
    referrerPolicy="no-referrer" onError={()=>setFailed(identity)}
    onLoad={event=>{if(event.currentTarget.naturalWidth<=2||event.currentTarget.naturalHeight<=2)setFailed(identity);}}/>
    {illustration&&<><span className="news-illustration-label">Ảnh minh họa{illustration.kind==='AI_CONCEPT'?' · AI':''}</span>
      <details className="news-image-credit" key={identity}><summary>Nguồn ảnh</summary><div>
        <p>{illustration.caption}</p><p><a href={illustration.sourceUrl} target="_blank" rel="noopener noreferrer">{illustration.title}</a> — {illustration.author} / {illustration.source}</p>
        <p><a href={illustration.licenseUrl} target="_blank" rel="noopener noreferrer">{illustration.license}</a> · {illustration.changes}</p>
        {illustration.derivativeLicense&&<p>Bản ảnh chỉnh sửa được phát hành theo <a href={illustration.derivativeLicenseUrl} target="_blank" rel="license noopener noreferrer">{illustration.derivativeLicense}</a>.</p>}
      </div></details></>}
    </div>;
}
