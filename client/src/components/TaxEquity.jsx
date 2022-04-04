import { Box, Divider, Paper, Typography } from '@mui/material'
import React, { useRef, useState } from 'react'
import UploadFile from './common/UploadFile'
import AddFilesIcon from '../assets/add-files.svg'
import { makeStyles } from '@mui/styles'
import UploadFiles from './common/UploadFiles'

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

const tempdata = [{ "category": "Short Term Capital Gain (STT paid)", "label": "loss", "pnl": 189838.69 }, { "category": "Short Term Capital Gain (STT paid)", "label": "profit", "pnl": 271110.5 }, { "category": "Speculation Income (STT paid)", "label": "loss", "pnl": 98426.22 }, { "category": "Speculation Income (STT paid)", "label": "profit", "pnl": 138592.35 }]


const TaxEquity = () => {

    const classes = useStyles()
    // const [firstload, setfirstload] = useState(true)
    // const [data, setdata] = useState([])
    const [data, setdata] = useState([])

    const onUpload = (params) => {
        console.log(params)
        setdata(params)
    }

    return (
        <Box sx={{ pt: 4 }}>
            {
                data.length === 0 ? (


                    <Box sx={{ display: { xs: 'flex', md: 'flex' }, alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                        <UploadFiles labelIdle='Import your stocks data to generate a report' cb={onUpload}>
                            <Box sx={{ height: { xs: 200, md: 200 }, mb: 4, mt: 2, ":hover": { cursor: 'pointer' } }} >
                                <img src={AddFilesIcon} alt="" style={{ width: 'inherit', height: 'inherit' }} />
                            </Box>
                        </UploadFiles>

                    </Box>

                ) : (
                    <Box elevation='1' sx={{ backgroundColor: '#FAFAFB', padding: 4, display: 'flex', }}>
                        {data.map((item, index) => (
                            <Box sx={{padding:1}}>
                                <Box>
                                    <Typography variant="caption" display="block" gutterBottom>
                                        {item.category} {item.label}
                                    </Typography>
                                </Box>
                                <Box>
                                    <Typography variant="h6" gutterBottom component="div">
                                        {item.pnl.toLocaleString()}
                                    </Typography>
                                </Box>
                            </Box>
                        ))}
                    </Box>
                )}
        </Box>
    )
}

export default TaxEquity