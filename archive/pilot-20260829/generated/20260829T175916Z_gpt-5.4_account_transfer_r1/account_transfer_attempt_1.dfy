module AccountTransfer {
  class Account {
    var balance: int

    predicate Valid()
      reads this
    {
      balance >= 0
    }

    constructor(initialBalance: int)
      requires initialBalance >= 0
      ensures Valid()
      ensures balance == initialBalance
    {
      balance := initialBalance;
    }
  }

  method Transfer(source: Account, destination: Account, amount: int)
    requires source != null
    requires destination != null
    requires source != destination
    requires source.Valid()
    requires destination.Valid()
    requires amount >= 0
    requires amount <= source.balance
    modifies source, destination
    ensures source.Valid()
    ensures destination.Valid()
    ensures source.balance == old(source.balance) - amount
    ensures destination.balance == old(destination.balance) + amount
    ensures source.balance + destination.balance == old(source.balance + destination.balance)
  {
    source.balance := source.balance - amount;
    destination.balance := destination.balance + amount;
  }
}
