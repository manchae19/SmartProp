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
import { reactive } from "../../shared/state/store.js";
import "./AiConfigView.css";
function setup(__props) {
  const state = reactive({
    config: {
      autoPriceSuggest: true,
      autoFlagDuplicate: true,
      mismatchAlert: true,
      autoHideSevere: false,
    },
  });
  const config = state.config;
  function handlePostAction() {
    alert("Chức năng đăng tin nhanh");
  }
  function resetDefaults() {
    alert("Đã khôi phục cấu hình mặc định!");
  }
  function saveConfig() {
    alert("Đã lưu cấu hình AI thành công!");
  }
  return {
    reactive,
    state,
    config,
    handlePostAction,
    resetDefaults,
    saveConfig,
  };
}
export default React.forwardRef(function AiConfigView(props, ref) {
  const ctx = useSetup(setup, props, ref);
  return rootProps(ctx, [
    <div data-ui-view="AiConfigView"
      {...mergeProps({
        className: "main",
        "data-sp-86a82bb3": "",
      })}
    >
      <p
        {...mergeProps({
          className: "text-xs text-brand-muted mb-4",
          "data-sp-86a82bb3": "",
        })}
      >
        {"Giao diện cấu hình AI; tính năng lưu chưa được kích hoạt."}
      </p>
      <div
        {...mergeProps({
          className: "section-header",
          "data-sp-86a82bb3": "",
        })}
      >
        <div
          {...mergeProps({
            className: "header-titles",
            "data-sp-86a82bb3": "",
          })}
        >
          <div
            {...mergeProps({
              className: "badge-tag",
              "data-sp-86a82bb3": "",
            })}
          >
            {"QUẢN TRỊ"}
          </div>
          <div
            {...mergeProps({
              className: "section-title",
              "data-sp-86a82bb3": "",
            })}
          >
            {"Cấu hình AI"}
          </div>
          <div
            {...mergeProps({
              className: "section-desc",
              "data-sp-86a82bb3": "",
            })}
          >
            {
              "Điều chỉnh tham số và ngưỡng cảnh báo cho các mô hình AI đang vận hành hệ thống."
            }
          </div>
        </div>
      </div>
      <div
        {...mergeProps({
          className: "ai-config-container",
          "data-sp-86a82bb3": "",
        })}
      >
        <div
          {...mergeProps({
            className: "config-card",
            "data-sp-86a82bb3": "",
          })}
        >
          <div
            {...mergeProps({
              className: "card-top",
              "data-sp-86a82bb3": "",
            })}
          >
            <div
              {...mergeProps({
                className: "card-info",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "card-title-row",
                  "data-sp-86a82bb3": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "card-title",
                    "data-sp-86a82bb3": "",
                  })}
                >
                  {"Định giá bất động sản"}
                </span>
                <span
                  {...mergeProps({
                    className: "badge-version",
                    "data-sp-86a82bb3": "",
                  })}
                >
                  {"XGBoost · v2.3"}
                </span>
              </div>
              <div
                {...mergeProps({
                  className: "card-desc",
                  "data-sp-86a82bb3": "",
                })}
              >
                {
                  "Dự đoán giá tham chiếu và các yếu tố ảnh hưởng (SHAP) cho tin đăng mới."
                }
              </div>
            </div>
            <div
              {...mergeProps({
                className: "card-meta",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "meta-highlight",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"MAE: 6.2%"}
              </div>
              <div
                {...mergeProps({
                  className: "meta-date",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Huấn luyện lại: 14/09/2026"}
              </div>
            </div>
          </div>
          <div
            {...mergeProps({
              className: "config-option",
              "data-sp-86a82bb3": "",
            })}
          >
            <div
              {...mergeProps({
                className: "option-info",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "option-title",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Gợi ý giá tự động cho tin đăng mới"}
              </div>
              <div
                {...mergeProps({
                  className: "option-desc",
                  "data-sp-86a82bb3": "",
                })}
              >
                {
                  "Hiển thị giá tham chiếu ngay khi người dùng nhập thông tin cơ bản."
                }
              </div>
            </div>
            <div
              {...mergeProps({
                className: ["toggle-switch", {
                  active: ctx.config.autoPriceSuggest,
                }],
                
                onClick: ($event) => {
                  ctx.config.autoPriceSuggest = !ctx.config.autoPriceSuggest;
                },
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "toggle-thumb",
                  "data-sp-86a82bb3": "",
                })}
              />
            </div>
          </div>
          <div
            {...mergeProps({
              className: "config-option",
              "data-sp-86a82bb3": "",
            })}
          >
            <div
              {...mergeProps({
                className: "option-info",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "option-title",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Độ lệch cảnh báo giá bất thường"}
              </div>
              <div
                {...mergeProps({
                  className: "option-desc",
                  "data-sp-86a82bb3": "",
                })}
              >
                {
                  "Gắn cờ tin đăng khi giá niêm yết lệch quá ngưỡng so với giá dự đoán."
                }
              </div>
            </div>
            <div
              {...mergeProps({
                className: "option-control",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "slider-mock",
                  "data-sp-86a82bb3": "",
                })}
              >
                <div
                  {...mergeProps({
                    className: "slider-fill",
                    style: "width: 30%",
                    "data-sp-86a82bb3": "",
                  })}
                />
              </div>
              <span
                {...mergeProps({
                  className: "control-value",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"± 15%"}
              </span>
            </div>
          </div>
        </div>
        <div
          {...mergeProps({
            className: "config-card",
            "data-sp-86a82bb3": "",
          })}
        >
          <div
            {...mergeProps({
              className: "card-top",
              "data-sp-86a82bb3": "",
            })}
          >
            <div
              {...mergeProps({
                className: "card-info",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "card-title-row",
                  "data-sp-86a82bb3": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "card-title",
                    "data-sp-86a82bb3": "",
                  })}
                >
                  {"Phát hiện ảnh trùng lặp"}
                </span>
                <span
                  {...mergeProps({
                    className: "badge-version",
                    "data-sp-86a82bb3": "",
                  })}
                >
                  {"Siamese Network · v1.4"}
                </span>
              </div>
              <div
                {...mergeProps({
                  className: "card-desc",
                  "data-sp-86a82bb3": "",
                })}
              >
                {
                  "So khớp ảnh tin đăng để phát hiện sao chép hoặc đăng trùng từ nguồn khác."
                }
              </div>
            </div>
            <div
              {...mergeProps({
                className: "card-meta",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "meta-highlight",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Độ chính xác: 91.4%"}
              </div>
              <div
                {...mergeProps({
                  className: "meta-date",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Huấn luyện lại: 08/09/2026"}
              </div>
            </div>
          </div>
          <div
            {...mergeProps({
              className: "config-option",
              "data-sp-86a82bb3": "",
            })}
          >
            <div
              {...mergeProps({
                className: "option-info",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "option-title",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Ngưỡng cảnh báo trùng ảnh"}
              </div>
              <div
                {...mergeProps({
                  className: "option-desc",
                  "data-sp-86a82bb3": "",
                })}
              >
                {'Tỉ lệ tương đồng tối thiểu để gắn cờ "nghi ngờ trùng ảnh".'}
              </div>
            </div>
            <div
              {...mergeProps({
                className: "option-control",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "slider-mock",
                  "data-sp-86a82bb3": "",
                })}
              >
                <div
                  {...mergeProps({
                    className: "slider-fill",
                    style: "width: 92%",
                    "data-sp-86a82bb3": "",
                  })}
                />
              </div>
              <span
                {...mergeProps({
                  className: "control-value",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"92%"}
              </span>
            </div>
          </div>
          <div
            {...mergeProps({
              className: "config-option",
              "data-sp-86a82bb3": "",
            })}
          >
            <div
              {...mergeProps({
                className: "option-info",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "option-title",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Tự động gắn cờ tin đăng nghi trùng ảnh"}
              </div>
              <div
                {...mergeProps({
                  className: "option-desc",
                  "data-sp-86a82bb3": "",
                })}
              >
                {
                  "Đưa tin đăng vào hàng chờ duyệt thủ công thay vì hiển thị ngay."
                }
              </div>
            </div>
            <div
              {...mergeProps({
                className: ["toggle-switch", {
                  active: ctx.config.autoFlagDuplicate,
                }],
                
                onClick: ($event) => {
                  ctx.config.autoFlagDuplicate = !ctx.config.autoFlagDuplicate;
                },
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "toggle-thumb",
                  "data-sp-86a82bb3": "",
                })}
              />
            </div>
          </div>
        </div>
        <div
          {...mergeProps({
            className: "config-card",
            "data-sp-86a82bb3": "",
          })}
        >
          <div
            {...mergeProps({
              className: "card-top",
              "data-sp-86a82bb3": "",
            })}
          >
            <div
              {...mergeProps({
                className: "card-info",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "card-title-row",
                  "data-sp-86a82bb3": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "card-title",
                    "data-sp-86a82bb3": "",
                  })}
                >
                  {"Nhận diện & đối chiếu tiện ích"}
                </span>
                <span
                  {...mergeProps({
                    className: "badge-version",
                    "data-sp-86a82bb3": "",
                  })}
                >
                  {"YOLOv8 · v1.1"}
                </span>
              </div>
              <div
                {...mergeProps({
                  className: "card-desc",
                  "data-sp-86a82bb3": "",
                })}
              >
                {
                  "Phát hiện tiện ích trong ảnh và đối chiếu với mô tả tin đăng."
                }
              </div>
            </div>
            <div
              {...mergeProps({
                className: "card-meta",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "meta-highlight",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"mAP: 0.87"}
              </div>
              <div
                {...mergeProps({
                  className: "meta-date",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Huấn luyện lại: 02/09/2026"}
              </div>
            </div>
          </div>
          <div
            {...mergeProps({
              className: "config-option",
              "data-sp-86a82bb3": "",
            })}
          >
            <div
              {...mergeProps({
                className: "option-info",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "option-title",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Độ tin cậy tối thiểu để nhận diện"}
              </div>
              <div
                {...mergeProps({
                  className: "option-desc",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Bỏ qua các phát hiện có độ tin cậy thấp hơn ngưỡng này."}
              </div>
            </div>
            <div
              {...mergeProps({
                className: "option-control",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "slider-mock",
                  "data-sp-86a82bb3": "",
                })}
              >
                <div
                  {...mergeProps({
                    className: "slider-fill",
                    style: "width: 70%",
                    "data-sp-86a82bb3": "",
                  })}
                />
              </div>
              <span
                {...mergeProps({
                  className: "control-value",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"70%"}
              </span>
            </div>
          </div>
          <div
            {...mergeProps({
              className: "config-option",
              "data-sp-86a82bb3": "",
            })}
          >
            <div
              {...mergeProps({
                className: "option-info",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "option-title",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Cảnh báo khi mô tả không khớp ảnh"}
              </div>
              <div
                {...mergeProps({
                  className: "option-desc",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Hiển thị nhãn cảnh báo cho người xem khi phát hiện sai lệch."}
              </div>
            </div>
            <div
              {...mergeProps({
                className: ["toggle-switch", {
                  active: ctx.config.mismatchAlert,
                }],
                
                onClick: ($event) => {
                  ctx.config.mismatchAlert = !ctx.config.mismatchAlert;
                },
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "toggle-thumb",
                  "data-sp-86a82bb3": "",
                })}
              />
            </div>
          </div>
        </div>
        <div
          {...mergeProps({
            className: "config-card",
            "data-sp-86a82bb3": "",
          })}
        >
          <div
            {...mergeProps({
              className: "card-top",
              "data-sp-86a82bb3": "",
            })}
          >
            <div
              {...mergeProps({
                className: "card-info",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "card-title-row",
                  "data-sp-86a82bb3": "",
                })}
              >
                <span
                  {...mergeProps({
                    className: "card-title",
                    "data-sp-86a82bb3": "",
                  })}
                >
                  {"Kiểm duyệt tự động"}
                </span>
              </div>
              <div
                {...mergeProps({
                  className: "card-desc",
                  "data-sp-86a82bb3": "",
                })}
              >
                {
                  "Quy tắc tự động ẩn hoặc gắn cờ tin đăng có dấu hiệu vi phạm nghiêm trọng."
                }
              </div>
            </div>
          </div>
          <div
            {...mergeProps({
              className: "config-option",
              "data-sp-86a82bb3": "",
            })}
          >
            <div
              {...mergeProps({
                className: "option-info",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "option-title",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Tự động ẩn tin đăng vi phạm nghiêm trọng"}
              </div>
              <div
                {...mergeProps({
                  className: "option-desc",
                  "data-sp-86a82bb3": "",
                })}
              >
                {
                  "Ẩn ngay lập tức khỏi kết quả tìm kiếm, chờ quản trị viên xem xét."
                }
              </div>
            </div>
            <div
              {...mergeProps({
                className: ["toggle-switch", {
                  active: ctx.config.autoHideSevere,
                }],
                
                onClick: ($event) => {
                  ctx.config.autoHideSevere = !ctx.config.autoHideSevere;
                },
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "toggle-thumb",
                  "data-sp-86a82bb3": "",
                })}
              />
            </div>
          </div>
          <div
            {...mergeProps({
              className: "config-option",
              "data-sp-86a82bb3": "",
            })}
          >
            <div
              {...mergeProps({
                className: "option-info",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "option-title",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"Điểm rủi ro tối thiểu để tự động ẩn"}
              </div>
              <div
                {...mergeProps({
                  className: "option-desc",
                  "data-sp-86a82bb3": "",
                })}
              >
                {
                  "Tổng hợp từ các tín hiệu: trùng ảnh, sai lệch mô tả, báo cáo người dùng."
                }
              </div>
            </div>
            <div
              {...mergeProps({
                className: "option-control",
                "data-sp-86a82bb3": "",
              })}
            >
              <div
                {...mergeProps({
                  className: "slider-mock",
                  "data-sp-86a82bb3": "",
                })}
              >
                <div
                  {...mergeProps({
                    className: "slider-fill",
                    style: "width: 85%",
                    "data-sp-86a82bb3": "",
                  })}
                />
              </div>
              <span
                {...mergeProps({
                  className: "control-value",
                  "data-sp-86a82bb3": "",
                })}
              >
                {"85 / 100"}
              </span>
            </div>
          </div>
        </div>
        <div
          {...mergeProps({
            className: "form-actions-bar",
            "data-sp-86a82bb3": "",
          })}
        >
          <div
            {...mergeProps({
              className: "action-notice",
              "data-sp-86a82bb3": "",
            })}
          >
            {
              " Thay đổi cấu hình sẽ áp dụng cho các tin đăng mới và có thể mất vài phút để đồng bộ tới toàn hệ thống. "
            }
          </div>
          <div
            {...mergeProps({
              className: "action-buttons",
              "data-sp-86a82bb3": "",
            })}
          >
            <button
              {...mergeProps({
                disabled: true,
                className: "btn-secondary",
                onClick: ($event) => {
                  return ctx.resetDefaults?.($event);
                },
                "data-sp-86a82bb3": "",
              })}
            >
              {"Khôi phục mặc định"}
            </button>
            <button
              {...mergeProps({
                disabled: true,
                className: "btn-success",
                onClick: ($event) => {
                  return ctx.saveConfig?.($event);
                },
                "data-sp-86a82bb3": "",
              })}
            >
              {"Lưu cấu hình"}
            </button>
          </div>
        </div>
      </div>
    </div>,
  ]);
});
