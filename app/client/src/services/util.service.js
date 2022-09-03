class UtilService {
    numberFormat(value) {
        return new Intl.NumberFormat('en-IN', {
          style: 'currency',
          currency: 'INR'
        }).format(value);
    }
}
export default new UtilService();