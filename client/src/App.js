import './App.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
// import Holdings from './components/finance/Holdings';
import Home from './components/Home';
// import FinanceDashboard from './components/finance/FinanceDashboard';
import Box from '@mui/material/Box';
import { Container, CssBaseline } from '@mui/material';
import Header from './components/common/Header';
import Sidebar from './components/common/Sidebar';
import Toolbar from '@mui/material/Toolbar';
// import BankAccounts from './components/finance/BankAccounts';
// import BankAccountDetails from './components/finance/BankAccountDetails';

import { createTheme, ThemeProvider } from '@mui/material/styles';
import Dashboard from './components/Dashboard';
import Tax from './components/Tax';
import { makeStyles } from '@mui/styles';
import TaxEquity from './components/TaxEquity';


const theme = createTheme();
const headerHeight = 48

const useStyles = makeStyles({
  toolbar:{
      height:headerHeight,
      minHeight:headerHeight
  }
})

function App() {
  const classes = useStyles()
  return (
    <ThemeProvider theme={theme}>
      <Router basename='stocks_analysis'>
      <Box >
        <CssBaseline />
        <Header />
        {/* <Sidebar /> */}
        <Box component="main" sx={{ flexGrow: 1, px:4 , backgroundColor:'white', minHeight:'100vh'}}>
          <Toolbar className={classes.toolbar} />
            <Container maxWidth='xl'>

           
            <Routes>
              <Route exact path="/" element={<Home />} />
              <Route exact path="/dashboard" element={<Dashboard />} />
              <Route exact path="/tax" element={<Tax />} >
                <Route path="/tax/" element={<>ok</>} />
                <Route path='/tax/equity' element={<TaxEquity/>} />
              </Route>
              {/* <Route exact path="/finance/holdings" element={<Holdings />} />
              <Route exact path="/finance" element={<FinanceDashboard />} />
              <Route exact path="/finance/bankaccounts" element={<BankAccounts />} >
                <Route
                  path="/finance/bankaccounts/details:account"
                  element={<BankAccountDetails />}
                />
              </Route> */}
            </Routes>
            </Container>
          
        </Box>

      </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;