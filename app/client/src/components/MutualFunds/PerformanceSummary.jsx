import React, { useEffect } from 'react'
import { Paper, Box, Typography, Skeleton, Stack } from '@mui/material'
import { blue, grey, blueGrey } from '@mui/material/colors';
import MutualFundService from '../../services/mutual-fund.services';
import { useState } from 'react';
import Highcharts from 'highcharts/highstock'
import HighchartsReact from 'highcharts-react-official'
import Grid from '@mui/material/Unstable_Grid2';

import UtilService from '../../services/util.service';

const PerformanceSummary = () => {

  const [summary, setsummary] = useState(null)
  const [performance, setperformance] = useState([])
  const [loading, setloading] = useState(false)

  useEffect(() => {

    setloading(true)
    MutualFundService.getPerformance().then(response => {
      setsummary(response.data.summary)
      setperformance(response.data.performance)
      setloading(false)
    }).catch(error => {
      console.log(error)
      setloading(false)
    })

    return () => {
      // second
    }
  }, [])


  return (
    <>
      {loading ? (

        <Box sx={{ width: '100%' }}>
          <Skeleton />
          <Skeleton animation="wave" />
          <Skeleton animation={false} />
        </Box>
      ) : (

        <>
          <Box sx={{ flexGrow: 1 }}>
            <Grid container spacing={2}>
              <Grid xs={4}>
                <>
                  <Box>
                    <Typography>Portfolio Summary</Typography>
                  </Box>
                  <Paper sx={{ padding: 1 }} elevation={1}>
                    {/* <Stack direction='row' spacing={4}> */}
                    <Box display={'flex'} flexDirection='column'>
                      <Typography variant="subtitle2" color={grey[500]} component="div">Current Value</Typography>
                      <Typography variant="h6" component="div">{UtilService.numberFormat(summary?.value)}</Typography>
                      <Typography variant="subtitle2" component="div">1 Day Change ₹ {UtilService.numberFormat(summary?.day_change)} ▼{summary?.day_change_perc}%</Typography>
                    </Box>
                    <Box display={'flex'} flexDirection='column'>
                      <Typography variant="subtitle2" color={grey[500]} component="div">Invested</Typography>
                      <Typography variant="h6" component="div">{UtilService.numberFormat(summary?.invested)}</Typography>
                    </Box>
                    <Box display={'flex'} flexDirection='column'>
                      <Typography variant="subtitle2" color={grey[500]} component="div">Returns</Typography>
                      <Typography variant="h6" component="div">{UtilService.numberFormat(summary?.total_return)}</Typography>
                    </Box>
                    <Box display={'flex'} flexDirection='column'>
                      <Typography variant="subtitle2" color={grey[500]} component="div">XIRR%</Typography>
                      <Typography variant="h6" component="div">{summary?.xirr_perc}%</Typography>
                    </Box>
                    {/* </Stack> */}
                  </Paper>
                </>
              </Grid>
              <Grid xs={8}>
                <Box>
                  <Typography>Portfolio Performance</Typography>
                </Box>
                <HighchartsReact
                  highcharts={Highcharts}
                  constructorType={"stockChart"}
                  options={{
                    rangeSelector: {
                      selected: 2
                    },

                    title: {
                      text: '',
                    },

                    scrollbar: {
                      enabled: false,
                    },

                    tooltip: {
                      formatter() {
                        let s = '<b>' + Highcharts.dateFormat('%b %e, %Y', this.x) + '</b>';

                        this.points.forEach(point => {
                          s += '<br/>Portfolio : ' + UtilService.numberFormat(point.y );
                        });

                        return s;
                      }
                    },

                    series: [{
                      name: 'Portfolio',
                      data: performance,
                    }]
                  }}
                />
              </Grid>
            </Grid>
          </Box>
        </>
      )}
    </>
  )
}

export default PerformanceSummary


