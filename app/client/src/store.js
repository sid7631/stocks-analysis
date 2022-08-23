import { configureStore } from '@reduxjs/toolkit'
import { mutualFundSlice } from './slices/mutualFundSlice'

export const store = configureStore({
  reducer: {
    mutualfund:mutualFundSlice.reducer
  },
})