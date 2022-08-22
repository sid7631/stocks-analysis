import axios from "axios";

function baseURLConfig() {
  console.log(process.env.NODE_ENV )
  if (process.env.NODE_ENV !== 'production') {
    return 'http://127.0.0.1:8080'
  }
  return ''
}

export default axios.create({
  
  baseURL: baseURLConfig(),
  headers: {
    "Content-type": "application/json"
  }
});