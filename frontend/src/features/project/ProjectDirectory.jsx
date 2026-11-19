import { classNames } from "../../shared/lib/ui.js";
import { createStateStore } from "../../shared/state/createStateStore.js";
import React, { useState, useSyncExternalStore, useRef } from "react";
import "./ProjectDirectory.css";
function useProjectDirectoryState(inputProps, forwardedRef) {
  inputProps = {
    limit: 6,
    ...inputProps
  };
  const _propsLatest = useRef(inputProps);
  _propsLatest.current = inputProps;
  ({
    limit: 6,
    ...inputProps
  });
  const [failedImages] = useState(() => createStateStore(new Set()));
  // Editorial directory of official project websites, independent of SmartProp listing data.
  // Local image copies retain imageSource for attribution and avoid third-party hotlink failures.
  useSyncExternalStore(failedImages.subscribe, failedImages.getSnapshot);
  const projects = [{
    name: "Sun Ponte Residence",
    image: "/media/projects/sun-ponte.jpg",
    imageSource: "https://sun-ecommerce-cdn.azureedge.net/ecommerce/service-sites/thumbnail/SunProperty/D%E1%BB%B1%20%C3%A1n/D%E1%BB%B1%20%C3%A1n%20BDS/Da%20Nang/Sun%20Ponte%20Residence/23395/image-thumb__23395__640/Sun%20Ponte%20Residence%203.jpg",
    publisher: "Sun Property",
    category: "Căn hộ & nhà thấp tầng",
    description: "Tổ hợp bên sông Hàn, gần cầu Rồng và cầu Trần Thị Lý.",
    url: "https://sunpropertygroup.vn/cac-du-an/sun-ponte-residence-9554"
  }, {
    name: "The Filmore Da Nang",
    image: "/media/projects/the-filmore.jpg",
    imageSource: "https://filmore.com.vn/thefilmoredanang/wp-content/uploads/2025/02/The-Filmore-Da-Nang-Life-Style-3.jpeg",
    publisher: "Filmore Development",
    category: "Căn hộ",
    description: "Tìm hiểu dự án, thiết kế và hình ảnh do Filmore Development công bố.",
    url: "https://filmore.com.vn/thefilmoredanang/"
  }, {
    name: "FPT Plaza 3",
    image: "/media/projects/fpt-plaza-3.jpg",
    imageSource: "https://fptcity.vn/wp-content/uploads/DJI_0033-600x450.jpg",
    publisher: "FPT City Đà Nẵng",
    category: "Chung cư",
    description: "Dự án chung cư thuộc Khu đô thị Công nghệ FPT Đà Nẵng.",
    url: "https://fptcity.vn/du-an/fpt-plaza-3/"
  }, {
    name: "Sun Symphony Residence",
    image: "/media/projects/sun-symphony.jpg",
    imageSource: "https://sun-ecommerce-cdn.azureedge.net/ecommerce/service-sites/thumbnail/SunProperty/D%E1%BB%B1%20%C3%A1n/D%E1%BB%B1%20%C3%A1n%20BDS/Da%20Nang/Sun%20Symphony%20Residence/23310/image-thumb__23310__640/Da-Nang-Toan-canh-Sun-Symphony-Residence-Da-Nang.jpg",
    publisher: "Sun Property",
    category: "Căn hộ & thương mại",
    description: "Quần thể căn hộ và không gian thương mại ven sông Hàn.",
    url: "https://sunpropertygroup.vn/cac-du-an/sun-symphony-residence-9528"
  }, {
    name: "Sunneva Island",
    image: "/media/projects/sunneva-island.jpg",
    imageSource: "https://sun-ecommerce-cdn.azureedge.net/ecommerce/service-sites/thumbnail/SunProperty/_default_upload_bucket/23382/image-thumb__23382__640/da-nang-du-an-sunneva-island-da-nang015_1765530780.a8cf4d13_1765530780.jpg",
    publisher: "Sun Property",
    category: "Khu đô thị",
    description: "Khu đô thị trên đảo Đồng Nò, phía nam thành phố Đà Nẵng.",
    url: "https://sunpropertygroup.vn/projects/sunneva-island-9550"
  }, {
    name: "Sun Cosmo Residence",
    image: "/media/projects/sun-cosmo.jpg",
    imageSource: "https://sun-ecommerce-cdn.azureedge.net/ecommerce/service-sites/thumbnail/SunProperty/D%E1%BB%B1%20%C3%A1n/D%E1%BB%B1%20%C3%A1n%20BDS/Da%20Nang/Sun%20Cosmo%20Residence/23377/image-thumb__23377__640/Da-Nang-Du-an-Sun-Cosmo-Residence.jpg",
    publisher: "Sun Property",
    category: "Căn hộ & nhà thấp tầng",
    description: "Tổ hợp căn hộ và nhà thấp tầng gần cầu Trần Thị Lý.",
    url: "https://sunpropertygroup.vn/cac-du-an/sun-cosmo-residence-9549"
  }].map(project => ({
    ...project,
    host: new URL(project.url).hostname
  }));
  return {
    ...inputProps,
    failedImages: failedImages.getSnapshot(),
    projects,
    rootAttributes: Object.fromEntries(Object.entries(inputProps).filter(([key]) => !["limit", "children", "ref", "key"].includes(key) && (!key.startsWith("on") || /^on(Click|DoubleClick|KeyDown|KeyUp|Change|Input|Focus|Blur|MouseDown|MouseUp|PointerDown)$/.test(key))))
  };
}
export default React.forwardRef(function ProjectDirectory(props, ref) {
  const view = useProjectDirectoryState(props, ref);
  return <><div aria-label="Website chính thức các dự án tại Đà Nẵng" data-sp-5114ab66="" {...view.rootAttributes} className={classNames(["project-directory", view.rootAttributes.className])}>
      {((items, render) => typeof items === "number" ? Array.from({
        length: Math.max(0, items)
      }, (_, index) => render(index + 1, index)) : Array.isArray(items) || typeof items === "string" ? Array.from(items).map(render) : Object.entries(items || {}).map(([key, item], index) => render(item, key, index)))(view.projects.slice(0, view.limit), (project, index) => <a key={project.url} href={project.url} target="_blank" rel="noopener noreferrer" className="project-reference" aria-label={"Xem " + project.name + " trên website " + project.publisher + " (mở trong tab mới)"} data-sp-5114ab66="">
          <div className="reference-image" data-sp-5114ab66="">
            {!view.failedImages.has(project.url) ? <img src={project.image} alt={"Ảnh giới thiệu " + project.name + " — " + project.publisher} loading="lazy" decoding="async" width="640" height="400" onError={$event => {
            view.failedImages.add(project.url);
          }} data-sp-5114ab66="" /> : <div className="reference-image-fallback" data-sp-5114ab66="">
                <span aria-hidden="true" data-sp-5114ab66="">
                  {"▧"}
                </span>
                <span data-sp-5114ab66="">
                  {"Chưa tải được ảnh dự án"}
                </span>
              </div>}
            {!view.failedImages.has(project.url) ? <div className="reference-image-shade" aria-hidden="true" data-sp-5114ab66="" /> : null}
            <div className="reference-top" data-sp-5114ab66="">
              <span className="reference-category" data-sp-5114ab66="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(project.category)}
              </span>
              <span className="reference-number" aria-hidden="true" data-sp-5114ab66="">
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(String(index + 1).padStart(2, "0"))}
              </span>
            </div>
            {!view.failedImages.has(project.url) ? <span className="reference-source" data-sp-5114ab66="">
                {"Ảnh giới thiệu · "}
                {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(project.publisher)}
              </span> : null}
          </div>
          <div className="reference-body" data-sp-5114ab66="">
            <p className="reference-publisher" data-sp-5114ab66="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(project.publisher)}
            </p>
            <h3 data-sp-5114ab66="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(project.name)}
            </h3>
            <p className="reference-description" data-sp-5114ab66="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(project.description)}
            </p>
          </div>
          <div className="reference-footer" data-sp-5114ab66="">
            <span className="reference-host" data-sp-5114ab66="">
              {(value => value == null ? "" : typeof value === "object" ? JSON.stringify(value) : String(value))(project.host)}
            </span>
            <span className="reference-cta" data-sp-5114ab66="">
              {"Xem dự án "}
              <span aria-hidden="true" data-sp-5114ab66="">
                {"↗"}
              </span>
            </span>
          </div>
        </a>)}
    </div></>;
});
