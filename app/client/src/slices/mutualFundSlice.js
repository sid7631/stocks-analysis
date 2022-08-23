import { createSlice } from '@reduxjs/toolkit'


const initialState = {
    task:{
        task_id:null,
        task_result:null,
        task_status:null,
    }
}

export const mutualFundSlice = createSlice({
    name:'mutualfund',
    initialState,
    reducers: {
        updateTask: (state, action) => {
            state.task = action.payload
        }
    },
})

export const { updateTask } =  mutualFundSlice.actions

export default mutualFundSlice

