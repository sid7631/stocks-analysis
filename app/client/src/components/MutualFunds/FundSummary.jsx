import React, { useEffect } from 'react'
import { Paper, Box, Typography, Skeleton, Stack, Avatar, Chip } from '@mui/material'
import { blue, grey, blueGrey } from '@mui/material/colors';
import MutualFundService from '../../services/mutual-fund.services';
import { useState } from 'react';
import Highcharts from 'highcharts/highstock'
import HighchartsReact from 'highcharts-react-official'
import Grid from '@mui/material/Unstable_Grid2';

import UtilService from '../../services/util.service';
import FolioCard from '../common/FolioCard';
import { useParams } from 'react-router-dom';
import TransactionCard from '../common/TransactionCard';

const FundSummary = (props) => {

  const [summary, setsummary] = useState(null)
  const [performance, setperformance] = useState([])
  const [folios, setfolios] = useState([])
  const [transactions, settransactions] = useState([])
  const [loading, setloading] = useState(false)
  const { isin } = useParams();

  useEffect(() => {
    setloading(true)
    MutualFundService.getAmcSummary(isin).then(response => {
      setperformance(response.data.performance)
      setsummary(response.data.summary)
      setfolios(response.data.folio_summary)
      settransactions(response.data.transactions)
      setloading(false)
    }).catch(error => {
      console.log(error)
      setloading(false)
    })

    return () => {
      // second
    }
  }, [])

  const cardAction = (param) => {
    //pass
  }

  return (
    <React.Fragment>
      {loading ? (
        <Box sx={{ width: '100%' }}>
          <Skeleton />
          <Skeleton animation="wave" />
          <Skeleton animation={false} />
        </Box>
      ) : (<>
        <Box sx={{ flexGrow: 1 }}>
          <Grid container spacing={2}>
            <Grid container spacing={2} xs={9} direction='column'>
              <Grid xs={12} md={12}>
                <Box sx={{ marginBottom: 2 }}>
                  <Stack sx={{ minHeight: 50 }} direction='row' spacing={2} alignItems='center'>
                    <Avatar
                      alt={summary?.name}
                      src="/static/images/avatar/1.jpg"
                      sx={{ width: 48, height: 48 }}
                    />
                    <Stack direction='column' spacing={0} justifyContent='center' alignItems='flex-start' mb={1}>
                      <Typography variant="h6" component="div">
                        {summary?.name}
                      </Typography>
                      <Chip label="Equity" size="small" />
                    </Stack>
                  </Stack>

                </Box>
                <Box>
                  <Stack direction='row' justifyContent={'space-between'} spacing={0} marginBottom={2}>
                    <Box display={'flex'} flexDirection='column'>
                      <Typography variant="subtitle2" color={grey[500]} component="div">Current Value</Typography>
                      <Typography variant="h6" component="div">{UtilService.numberFormat(summary?.value)}</Typography>
                      <Typography variant="subtitle2" component="div">Invested {UtilService.numberFormat(summary?.invested)}</Typography>
                    </Box>
                    <Box display={'flex'} flexDirection='column'>
                      <Typography variant="subtitle2" color={grey[500]} component="div">Returns</Typography>
                      <Typography variant="h6" component="div">{UtilService.numberFormat(summary?.profit)}</Typography>
                    </Box>
                  </Stack>
                </Box>
                <HighchartsReact
                  highcharts={Highcharts}
                  constructorType={"stockChart"}
                  options={{
                    rangeSelector: {
                      selected: 4
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
                          s += '<br/>Portfolio : ' + UtilService.numberFormat(point.y);
                        });

                        return s;
                      }
                    },

                    series: [{
                      name: 'Portfolio',
                      data: performance,
                    }],
                    credits: {
                      enabled: false
                    }
                  }}
                />
              </Grid>
              <Grid xs={12} md={12}>
                <Box sx={{ marginBottom: 2 }}>
                  <Typography>Folios</Typography>
                </Box>
                <Grid container spacing={2} xs={12} >
                  {folios.map((item, index) => (
                    <Grid xs={12} sm={6} md={4} lg={4} key={index} >
                      <FolioCard data={item} action={cardAction}></FolioCard>
                    </Grid>
                  ))}

                </Grid>
              </Grid>
            </Grid>

            <Grid container spacing={2} xs={3} direction='column'>
              <Grid xs={12}>
                <Box sx={{ mb: 2, mt: 4 }}>
                  <Typography variant="h6">Transactions</Typography>
                </Box>
                <Box>

                <Grid container spacing={2} xs={12} direction='column' >
                  {transactions.map((item, index) => (
                    <Grid xs={12} sm={12} md={12} lg={12} key={index} >
                      <TransactionCard data={item} action={cardAction}></TransactionCard>
                    </Grid>
                  ))}

                </Grid>
                </Box>
              </Grid>
            </Grid>
          </Grid>
        </Box>
      </>)}
    </React.Fragment>
  )
}

export default FundSummary