import { useEffect, useRef } from 'react'

// See: https://usehooks-ts.com/react-hook/use-isomorphic-layout-effect
import  useIsomorphicLayoutEffect  from './useIsomorphicLayoutEffect'

function useInterval(callback, delay, stopFlag) {
  const savedCallback = useRef(callback)

  // Remember the latest callback if it changes.
  useIsomorphicLayoutEffect(() => {
    savedCallback.current = callback
  }, [callback])

  // Set up the interval.
  useEffect(() => {
    // Don't schedule if no delay is specified.
    // Note: 0 is a valid value for delay.
    let id
    function tick() {
      savedCallback.current()
      if(stopFlag) {
        clearInterval(id)
      }
    }
    if (delay !== null && !stopFlag) {
      id = setInterval(tick, delay)
      return () => clearInterval(id)
    }
  }, [delay, stopFlag])
}

export default useInterval
