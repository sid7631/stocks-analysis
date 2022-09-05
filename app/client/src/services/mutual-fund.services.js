import http from "../http-common";
class MutualFundService {
    getPerformance() {
        return http.get("/api/mutualfund");
    }

    getAmcSummary(isin) {
        return http.get("/api/amc/"+isin)
    }
}
export default new MutualFundService();