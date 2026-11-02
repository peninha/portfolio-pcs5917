// Background reads must check again after awaiting the server: a file chooser
// or an edit may have started while the request was in flight.
export function createStateRefresh({load,apply,canRefresh}) {
  let sequence=0,pending=0;
  return {
    get pending(){return pending>0;},
    async refresh({background=false}={}) {
      if(background&&!canRefresh())return false;
      const current=++sequence;pending++;
      try {
        const next=await load();
        if(current!==sequence||(background&&!canRefresh()))return false;
        apply(next);return true;
      } finally {pending--;}
    }
  };
}
