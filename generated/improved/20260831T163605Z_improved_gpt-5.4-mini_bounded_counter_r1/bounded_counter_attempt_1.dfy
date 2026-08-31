class Counter {
  var value: int
  var max: nat

  predicate Valid()
    reads this
  {
    0 <= value <= max
  }

  invariant Valid()

  constructor (m: nat)
    ensures Valid()
    ensures max == m
    ensures value == 0
  {
    max := m;
    value := 0;
  }

  method Increment()
    modifies this
    ensures Valid()
    ensures max == old(max)
    ensures value == if old(value) < old(max) then old(value) + 1 else old(value)
  {
    if value < max {
      value := value + 1;
    }
  }

  method Reset()
    modifies this
    ensures Valid()
    ensures max == old(max)
    ensures value == 0
  {
    value := 0;
  }
}
