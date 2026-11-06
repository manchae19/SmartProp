import React from "react";
import {
  useSetup,
  propsForSetup,
  emitForProps,
  exposeForSetup,
} from "../../shared/state/store.js";
import {
  mergeProps,
  bindRef,
  renderList,
  display,
  modelProps,
  rootProps,
  Teleport,
} from "../../shared/components/rendering.js";
import { RouterLink, RouterView } from "../../shared/routing/router.jsx";
import { ref } from "../../shared/state/store.js";
import "./ProjectDirectory.css";
function setup(__props) {
  propsForSetup(__props, { limit: { type: Number, default: 6 } });
  const failedImages = ref(new Set());
  // Editorial directory of official project websites, independent of SmartProp listing data.
  // Local image copies retain imageSource for attribution and avoid third-party hotlink failures.
  const projects = [
    {
      name: "Sun Ponte Residence",
      image: "/media/projects/sun-ponte.jpg",
      imageSource:
        "https://sun-ecommerce-cdn.azureedge.net/ecommerce/service-sites/thumbnail/SunProperty/D%E1%BB%B1%20%C3%A1n/D%E1%BB%B1%20%C3%A1n%20BDS/Da%20Nang/Sun%20Ponte%20Residence/23395/image-thumb__23395__640/Sun%20Ponte%20Residence%203.jpg",
      publisher: "Sun Property",
      category: "Căn hộ & nhà thấp tầng",
      description: "Tổ hợp bên sông Hàn, gần cầu Rồng và cầu Trần Thị Lý.",
      url: "https://sunpropertygroup.vn/cac-du-an/sun-ponte-residence-9554",
    },
    {
      name: "The Filmore Da Nang",
      image: "/media/projects/the-filmore.jpg",
      imageSource:
        "https://filmore.com.vn/thefilmoredanang/wp-content/uploads/2025/02/The-Filmore-Da-Nang-Life-Style-3.jpeg",
      publisher: "Filmore Development",
      category: "Căn hộ",
      description:
        "Tìm hiểu dự án, thiết kế và hình ảnh do Filmore Development công bố.",
      url: "https://filmore.com.vn/thefilmoredanang/",
    },
    {
      name: "FPT Plaza 3",
      image: "/media/projects/fpt-plaza-3.jpg",
      imageSource: "https://fptcity.vn/wp-content/uploads/DJI_0033-600x450.jpg",
      publisher: "FPT City Đà Nẵng",
      category: "Chung cư",
      description: "Dự án chung cư thuộc Khu đô thị Công nghệ FPT Đà Nẵng.",
      url: "https://fptcity.vn/du-an/fpt-plaza-3/",
    },
    {
      name: "Sun Symphony Residence",
      image: "/media/projects/sun-symphony.jpg",
      imageSource:
        "https://sun-ecommerce-cdn.azureedge.net/ecommerce/service-sites/thumbnail/SunProperty/D%E1%BB%B1%20%C3%A1n/D%E1%BB%B1%20%C3%A1n%20BDS/Da%20Nang/Sun%20Symphony%20Residence/23310/image-thumb__23310__640/Da-Nang-Toan-canh-Sun-Symphony-Residence-Da-Nang.jpg",
      publisher: "Sun Property",
      category: "Căn hộ & thương mại",
      description: "Quần thể căn hộ và không gian thương mại ven sông Hàn.",
      url: "https://sunpropertygroup.vn/cac-du-an/sun-symphony-residence-9528",
    },
    {
      name: "Sunneva Island",
      image: "/media/projects/sunneva-island.jpg",
      imageSource:
        "https://sun-ecommerce-cdn.azureedge.net/ecommerce/service-sites/thumbnail/SunProperty/_default_upload_bucket/23382/image-thumb__23382__640/da-nang-du-an-sunneva-island-da-nang015_1765530780.a8cf4d13_1765530780.jpg",
      publisher: "Sun Property",
      category: "Khu đô thị",
      description: "Khu đô thị trên đảo Đồng Nò, phía nam thành phố Đà Nẵng.",
      url: "https://sunpropertygroup.vn/projects/sunneva-island-9550",
    },
    {
      name: "Sun Cosmo Residence",
      image: "/media/projects/sun-cosmo.jpg",
      imageSource:
        "https://sun-ecommerce-cdn.azureedge.net/ecommerce/service-sites/thumbnail/SunProperty/D%E1%BB%B1%20%C3%A1n/D%E1%BB%B1%20%C3%A1n%20BDS/Da%20Nang/Sun%20Cosmo%20Residence/23377/image-thumb__23377__640/Da-Nang-Du-an-Sun-Cosmo-Residence.jpg",
      publisher: "Sun Property",
      category: "Căn hộ & nhà thấp tầng",
      description: "Tổ hợp căn hộ và nhà thấp tầng gần cầu Trần Thị Lý.",
      url: "https://sunpropertygroup.vn/cac-du-an/sun-cosmo-residence-9549",
    },
  ].map((project) => ({
    ...project,
    host: new URL(project.url).hostname,
  }));
  return {
    ref,
    failedImages,
    projects,
  };
}
export default React.forwardRef(function ProjectDirectory(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div
      {...mergeProps({
        className: "project-directory",
        "aria-label": "Website chính thức các dự án tại Đà Nẵng",
        "data-sp-5114ab66": "",
      })}
    >
      {renderList(ctx.projects.slice(0, ctx.limit), (project, index) => (
        <a
          key={project.url}
          {...mergeProps({
            href: project.url,
            target: "_blank",
            rel: "noopener noreferrer",
            className: "project-reference",
            "aria-label":
              "Xem " +
              project.name +
              " trên website " +
              project.publisher +
              " (mở trong tab mới)",
            "data-sp-5114ab66": "",
          })}
        >
          <div
            {...mergeProps({
              className: "reference-image",
              "data-sp-5114ab66": "",
            })}
          >
            {!ctx.failedImages.has(project.url) ? (
              <img
                {...mergeProps({
                  src: project.image,
                  alt:
                    "Ảnh giới thiệu " +
                    project.name +
                    " — " +
                    project.publisher,
                  loading: "lazy",
                  decoding: "async",
                  width: "640",
                  height: "400",
                  onError: ($event) => {
                    ctx.failedImages.add(project.url);
                  },
                  "data-sp-5114ab66": "",
                })}
              />
            ) : (
              <div
                {...mergeProps({
                  className: "reference-image-fallback",
                  "data-sp-5114ab66": "",
                })}
              >
                <span
                  {...mergeProps({
                    "aria-hidden": "true",
                    "data-sp-5114ab66": "",
                  })}
                >
                  {"▧"}
                </span>
                <span
                  {...mergeProps({
                    "data-sp-5114ab66": "",
                  })}
                >
                  {"Chưa tải được ảnh dự án"}
                </span>
              </div>
            )}
            {!ctx.failedImages.has(project.url) ? (
              <div
                {...mergeProps({
                  className: "reference-image-shade",
                  "aria-hidden": "true",
                  "data-sp-5114ab66": "",
                })}
              />
            ) : null}
            <div
              {...mergeProps({
                className: "reference-top",
                "data-sp-5114ab66": "",
              })}
            >
              <span
                {...mergeProps({
                  className: "reference-category",
                  "data-sp-5114ab66": "",
                })}
              >
                {display(project.category)}
              </span>
              <span
                {...mergeProps({
                  className: "reference-number",
                  "aria-hidden": "true",
                  "data-sp-5114ab66": "",
                })}
              >
                {display(String(index + 1).padStart(2, "0"))}
              </span>
            </div>
            {!ctx.failedImages.has(project.url) ? (
              <span
                {...mergeProps({
                  className: "reference-source",
                  "data-sp-5114ab66": "",
                })}
              >
                {"Ảnh giới thiệu · "}
                {display(project.publisher)}
              </span>
            ) : null}
          </div>
          <div
            {...mergeProps({
              className: "reference-body",
              "data-sp-5114ab66": "",
            })}
          >
            <p
              {...mergeProps({
                className: "reference-publisher",
                "data-sp-5114ab66": "",
              })}
            >
              {display(project.publisher)}
            </p>
            <h3
              {...mergeProps({
                "data-sp-5114ab66": "",
              })}
            >
              {display(project.name)}
            </h3>
            <p
              {...mergeProps({
                className: "reference-description",
                "data-sp-5114ab66": "",
              })}
            >
              {display(project.description)}
            </p>
          </div>
          <div
            {...mergeProps({
              className: "reference-footer",
              "data-sp-5114ab66": "",
            })}
          >
            <span
              {...mergeProps({
                className: "reference-host",
                "data-sp-5114ab66": "",
              })}
            >
              {display(project.host)}
            </span>
            <span
              {...mergeProps({
                className: "reference-cta",
                "data-sp-5114ab66": "",
              })}
            >
              {"Xem dự án "}
              <span
                {...mergeProps({
                  "aria-hidden": "true",
                  "data-sp-5114ab66": "",
                })}
              >
                {"↗"}
              </span>
            </span>
          </div>
        </a>
      ))}
    </div>,
  ]);
});
