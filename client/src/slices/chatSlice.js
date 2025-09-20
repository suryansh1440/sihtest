import { createSlice,nanoid } from '@reduxjs/toolkit'


const initialState = {
    chats:[],
    thought:[]

}

export const chatSlice = createSlice({
    name:'chat',
    initialState,
    reducers:{
        addMessage:(state,action)=>{
            state.chats.push({...action.payload,id:nanoid()})
             
        },
        connectSocket:(state,action)=>{

        },
        disconnectSocket:(state,action)=>{

        },
        subscribeToChat:(state,action)=>{
            
        }
    }
})

export const { addMessage } = chatSlice.actions

export default chatSlice.reducer