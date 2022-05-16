import { Box, Divider, Paper, Stack, Typography } from '@mui/material'
import React, { useRef, useState } from 'react'
import UploadFile from './common/UploadFile'
import AddFilesIcon from '../assets/add-files.svg'
import { makeStyles } from '@mui/styles'
import UploadFiles from './common/UploadFiles'
import DatePicker from './common/DatePicker'
import IconButton from '@mui/material/IconButton';
import Fingerprint from '@mui/icons-material/Fingerprint';
import EastIcon from '@mui/icons-material/East';
import FilterService from '../services/filter.service'
import moment from 'moment'

const useStyles = makeStyles({
    uploadLabel: {

        position: 'relative',

        '&:before': {
            content: "",
            position: 'absolute',
            left: 1,
            top: 0,
            bottom: 0,
            width: 180,
            background: 'url(AddFilesIcon)',
            color: 'red'
        }
    }
})

const datePickersMeta = {
    to: 'To',
    from: 'From'
}

const tempdata = [{ "category": "Short Term Capital Gain (STT paid)", "label": "loss", "pnl": 189838.69 }, { "category": "Short Term Capital Gain (STT paid)", "label": "profit", "pnl": 271110.5 }, { "category": "Speculation Income (STT paid)", "label": "loss", "pnl": 98426.22 }, { "category": "Speculation Income (STT paid)", "label": "profit", "pnl": 138592.35 }]


const TaxEquity = () => {

    const classes = useStyles()
    // const [firstload, setfirstload] = useState(true)
    const [data, setdata] = useState([])
    // const [data, setdata] = useState(tempdata)
    const [toDate, settoDate] = useState(null)
    const [fromDate, setfromDate] = useState(null)

    const onUpload = (params) => {
        setdata(params.records)
    }

    const updateTo = (label, params) => {
        if (label === datePickersMeta['to']) {
            settoDate(params)
        } else if (label === datePickersMeta['from']) {
            setfromDate(params)
        }
    }

    const filterDate = () => {
        console.log(moment(toDate).format('DD-MM-yyyy'))

        FilterService.filterDate(moment(fromDate).format('DD-MM-yyyy'), moment(toDate).format('DD-MM-yyyy'))
            .then((response) => {
                console.log(response.data.records)
                if (response.data.records.length){
                    setdata(response.data.records)
                }else {
                    alert('No data for selected date')
                }
            })
            .catch((error) => console.log(error))
    }

    return (
        <Box sx={{ pt: 4 }}>
            {
                data.length === 0 ? (
                    <Box sx={{ display: { xs: 'flex', md: 'flex' }, alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                        <UploadFiles labelIdle='Import your stocks data to generate a report' url="/api/upload/tax" cb={onUpload}>
                            <Box sx={{ height: { xs: 200, md: 200 }, mb: 4, mt: 2, ":hover": { cursor: 'pointer' } }} >
                                <img src={AddFilesIcon} alt="" style={{ width: 'inherit', height: 'inherit' }} />
                            </Box>
                        </UploadFiles>
                    </Box>
                ) : (
                    <>
                        {/* <Box sx={{display:'flex', alignItems:'center'}}> */}
                        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={{ xs: 1, sm: 2, md: 4 }} mb={2}>
                            <DatePicker cb={updateTo} label={datePickersMeta['from']} />
                            <DatePicker cb={updateTo} label={datePickersMeta['to']}  />
                            <IconButton aria-label="fingerprint" color="primary" onClick={filterDate}>
                                <EastIcon />
                            </IconButton>
                        </Stack>
                        {/* </Box> */}
                        <Box elevation='1' sx={{ backgroundColor: '#FAFAFB', padding: 4 }}>
                            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={{ xs: 1, sm: 2, md: 4 }}>

                                {data.length && data.map((item, index) => (
                                    <Box sx={{ padding: 1 }}>
                                        <Box>
                                            <Typography variant="caption" display="block" gutterBottom>
                                                {item.category} {item.label}
                                            </Typography>
                                        </Box>
                                        <Box sx={{display:'flex', alignItems:'baseline'}}>
                                            <Typography variant="h6" gutterBottom component="div" mr={0.5}>
                                            &#8377;
                                            </Typography>
                                            <Typography variant="h6" gutterBottom component="div" sx={{color:item.label==='loss'?'#E75757':'green'}}>
                                            {item.pnl.toLocaleString()}
                                            </Typography>
                                        </Box>
                                    </Box>
                                ))}
                            </Stack>
                        </Box>
                    </>
                )}
        </Box>
    )
}

export default TaxEquity