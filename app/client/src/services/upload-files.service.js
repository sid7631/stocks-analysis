import http from "../http-common";
class UploadFilesService {
    upload(url,file, onUploadProgress) {
        let formData = new FormData();
        formData.append("file", file);
        return http.post(url, formData, {
            headers: {
                "Content-Type": "multipart/form-data",
            },
            onUploadProgress,
        });
    }
    getFiles() {
        return http.get("/files");
    }
}
export default new UploadFilesService();