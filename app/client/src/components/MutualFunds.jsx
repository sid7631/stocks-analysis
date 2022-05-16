import { Box, Typography } from '@mui/material'
import React, { useState } from 'react'
import UploadFiles from './common/UploadFiles'
import AddFilesIcon from '../assets/add-files.svg'
import WorkOutlineIcon from '@mui/icons-material/WorkOutline';



const MutualFunds = () => {

    const [data, setdata] = useState([])

    const onUpload = (params) => {
        setdata(params.records)
    }

    return (
        <>
            <Box sx={{ display: 'flex', alignItems: 'center', paddingY: 4 }}>
                <WorkOutlineIcon fontSize='small' />
                <Typography variant="h6" sx={{ mx: 1 }}>
                    Mutual Fund Portfolio
                </Typography>
            </Box>
            <Box sx={{ pt: 4 }}>
                {
                    data.length === 0 ? (
                        <Box sx={{ display: { xs: 'flex', md: 'flex' }, alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                            <UploadFiles labelIdle='Import your stocks data to generate a report' url="/api/upload/mutualfund" cb={onUpload}>
                                <Box sx={{ height: { xs: 200, md: 200 }, mb: 4, mt: 2, ":hover": { cursor: 'pointer' } }} >
                                    <img src={AddFilesIcon} alt="" style={{ width: 'inherit', height: 'inherit' }} />
                                </Box>
                            </UploadFiles>
                        </Box>
                    ) : (
                        <>
                            <div>data available</div>
                        </>
                    )
                }
            </Box>
        </>
    )
}

export default MutualFunds