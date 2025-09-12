import { createSlice,nanoid } from '@reduxjs/toolkit'


const initialState = {
    chats:[]

}

export const chatSlice = createSlice({
    name:'chat',
    initialState,
    reducers:{
        addMessage:(state,action)=>{
            state.chats.push({...action.payload,id:nanoid()})
             
        },
    }
})

export const { addMessage } = chatSlice.actions

export default chatSlice.reducer