import React, { useState } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { Box, Button, Typography } from '@mui/material'
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
import { updateTask } from '../slices/mutualFundSlice'
import useInterval from '../hooks/useInterval'
import Alert from '@mui/material/Alert';
import Stack from '@mui/material/Stack';

import http from '../http-common'

const MutualFunds = () => {

    const [data, setdata] = useState([])
    const [value, setValue] = React.useState(0);

    const task = useSelector((state) => state.mutualfund.task)
    const dispatch = useDispatch()

    const handleChange = ( newValue) => {
        setValue(newValue);
    };

    const onUpload = (params) => {
        dispatch(updateTask(params))
    }

    useInterval(
        () => {
            http.get("/api/tasks/" + task.task_id).then((result) => dispatch(updateTask(result.data)))
        },
        5000,
        task.task_status == 'SUCCESS' || !task.task_id

    )

    const clearTask = () => {
        dispatch(updateTask(
            {
                task_id: null,
                task_result: null,
                task_status: null,
            }
        ))
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
                <TabsUnstyled value={value} onChange={(e)=> console.log('clicked',e.target.value)}>
                    <Box>

                        <TabsList>
                            <Tab component={Button} onClick={()=> handleChange(0)}>Performance Summary</Tab>
                            <Tab component={Button} onClick={()=> handleChange(1)}>My Mutual Funds</Tab>
                            <Tab component={Button} onClick={()=> handleChange(2)}>Insights</Tab>
                            <Tab component={Button} onClick={()=> handleChange(3)}>Add Mutual Funds</Tab>
                        </TabsList>
                    </Box>
                    <TabPanelUnstyled value={0}><PerformanceSummary /></TabPanelUnstyled>
                    <TabPanelUnstyled value={1}><Details /></TabPanelUnstyled>
                    <TabPanelUnstyled value={2}><Insights /></TabPanelUnstyled>
                    <TabPanelUnstyled value={3}>
                        {
                            task.task_status ?
                                (
                                    <Box sx={{ display: { xs: 'flex', md: 'flex' }, alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                                        {
                                            task.task_status === 'SUCCESS' && (
                                                <Stack spacing={2} direction="row">
                                                    <Alert severity="success">Mutual Funds Updated — <strong style={{cursor:'pointer'}} onClick={()=> handleChange(0)}>check it out!</strong></Alert>
                                                    <Button variant="text" onClick={clearTask}>Add More</Button>
                                                </Stack>
                                            )
                                        }
                                        {

                                            task.task_status === 'PENDING' && (
                                                <Alert severity="info">Mutual Funds Update in Progress!</Alert>
                                            )
                                        }

                                        {
                                            task.task_status === 'ERROR' && (
                                                <Stack spacing={2} direction="row">
                                                    <Alert severity="error">Mutual Funds Update Error — try again later!</Alert>
                                                    <Button variant="text" onClick={clearTask}>Try Again</Button>
                                                </Stack>
                                            )

                                        }
                                    </Box>
                                ) :
                                (
                                    <Box sx={{ display: { xs: 'flex', md: 'flex' }, alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
                                        <UploadFiles labelIdle='Import your mutual funds' url="/api/upload/mutualfund" cb={onUpload}>
                                            <Box sx={{ height: { xs: 200, md: 200 }, mb: 4, mt: 2, ":hover": { cursor: 'pointer' } }} >
                                                <img src={AddFilesIcon} alt="" style={{ width: 'inherit', height: 'inherit' }} />
                                            </Box>
                                        </UploadFiles>
                                    </Box>
                                )
                        }

                    </TabPanelUnstyled>
                </TabsUnstyled>
            </Box>
            <Box sx={{ pt: 4 }}>
                {
                    data.length === 0 ? (
                        <> no data</>
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