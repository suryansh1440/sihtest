import { createSlice} from '@reduxjs/toolkit'


const initialState = {
    isChatMapOpen:false,
    selectedMap:null,

}

export const chatMapSlice = createSlice({
    name:'chatMap',
    initialState,
    reducers:{
        setIsChatMapOpen:(state,action)=>{
            console.log(action.payload)
            state.isChatMapOpen = action.payload
        },
        setSelectedMap:(state,action)=>{
            state.selectedMap = action.payload
        },
    }
})

export const { setIsChatMapOpen, setSelectedMap } = chatMapSlice.actions

export default chatMapSlice.reducer