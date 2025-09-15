import { createSlice} from '@reduxjs/toolkit'


const initialState = {
    isChatMapOpen:true,

}

export const chatMapSlice = createSlice({
    name:'chatMap',
    initialState,
    reducers:{
        setIsChatMapOpen:(state,action)=>{
            console.log(action.payload)
            state.isChatMapOpen = action.payload
        },
    }
})

export const { setIsChatMapOpen } = chatMapSlice.actions

export default chatMapSlice.reducer