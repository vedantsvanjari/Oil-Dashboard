import { addDays, nextWednesday, setHours, setMinutes } from 'date-fns';

export function getNextEIARelease() {
  const now = new Date();
  let wed = nextWednesday(now);
  wed = setHours(wed, 10);
  wed = setMinutes(wed, 30);
  if (wed.getTime() < now.getTime()) {
    wed = nextWednesday(addDays(wed, 1));
    wed = setHours(wed, 10);
    wed = setMinutes(wed, 30);
  }
  return wed;
}
