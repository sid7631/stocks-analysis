const _ = require('lodash')

const tempdata = [
    {
        "Description": "Short Term Capital Gain (STT paid)",
        "Profit\\/Loss(-)": 189838.69,
        "label": "loss"
    },
    {
        "Description": "Short Term Capital Gain (STT paid)",
        "Profit\\/Loss(-)": 271110.5,
        "label": "profit"
    },
    {
        "Description": "Speculation Income (STT paid)",
        "Profit\\/Loss(-)": 98426.22,
        "label": "loss"
    },
    {
        "Description": "Speculation Income (STT paid)",
        "Profit\\/Loss(-)": 138592.35,
        "label": "profit"
    }
]

const data = _.mapValues(_.groupBy(tempdata,'Description'),clist => clist.map(item => {
            return {label:item['label'],value:item['Profit\\/Loss(-)']}
        }
    )
)

console.log(data)