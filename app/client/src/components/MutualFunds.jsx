import { Box, Button, Typography } from '@mui/material'
import React, { useState } from 'react'
import UploadFiles from './common/UploadFiles'
import AddFilesIcon from '../assets/add-files.svg'
import WorkOutlineIcon from '@mui/icons-material/WorkOutline';
import PropTypes from 'prop-types';
import { Tab, TabsList } from './common/Tabs'
import { styled } from '@mui/system';
import { buttonUnstyledClasses } from '@mui/base/ButtonUnstyled';
import TabUnstyled, { tabUnstyledClasses } from '@mui/base/TabUnstyled';


import TabsUnstyled from '@mui/base/TabsUnstyled';
import TabPanelUnstyled from '@mui/base/TabPanelUnstyled';
import PerformanceSummary from './MutualFunds/PerformanceSummary';
import Details from './MutualFunds/Details';
import Insights from './MutualFunds/Insights';


const MutualFunds = () => {

    const [data, setdata] = useState([])
    const [value, setValue] = React.useState(0);

    const handleChange = (event, newValue) => {
        setValue(newValue);
    };


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
            <Box>
                <TabsUnstyled defaultValue={0}>
                    <Box>

                        <TabsList>
                            <Tab component={Button}>Performance Summary</Tab>
                            <Tab component={Button}>My Mutual Funds</Tab>
                            <Tab component={Button}>Insights</Tab>
                        </TabsList>
                    </Box>
                    <TabPanelUnstyled value={0}><PerformanceSummary /></TabPanelUnstyled>
                    <TabPanelUnstyled value={1}><Details /></TabPanelUnstyled>
                    <TabPanelUnstyled value={2}><Insights /></TabPanelUnstyled>
                </TabsUnstyled>
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