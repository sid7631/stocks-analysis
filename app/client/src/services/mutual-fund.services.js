import http from "../http-common";
class MutualFundService {
    getPerformance() {
        return http.get("/api/mutualfund");
    }
}
export default new MutualFundService();