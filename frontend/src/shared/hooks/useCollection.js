import {api,errorText} from "../../features/auth/api.js";
import {usePagedResource} from "./usePagedResource.js";
export function useCollection(endpoint, summaryEndpoint, filters) {
  const request = async (...args) => {
    try {
      return await api(...args);
    } catch (error) {
      error.message = errorText(error);
      throw error;
    }
  };
  return usePagedResource(request, endpoint, filters, summaryEndpoint, {
    delay: 250,
    loadingDuringDelay: false
  });
}
