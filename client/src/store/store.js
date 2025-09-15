import { configureStore } from '@reduxjs/toolkit'
import chatReducer from '../slices/chatSlice'
import chatMapReducer from '../slices/chatmap'

export const store = configureStore({
  reducer: {
    chat: chatReducer,
    chatMap: chatMapReducer,
  },
})

export default store
