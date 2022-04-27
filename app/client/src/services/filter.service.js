import http from "../http-common";
class FilterService {
    filterDate(to,from) {
        return http.get("/api/tax/filter", {params:{to:to,from:from}});
    }
}
export default new FilterService();