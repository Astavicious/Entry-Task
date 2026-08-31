module AccountTransfer {
  class Account {
    var balance: nat

    constructor(initialBalance: nat)
      ensures balance == initialBalance
    {
      balance := initialBalance;
    }
  }

  method Transfer(source: Account, destination: Account, amount: nat)
    requires source != destination
    requires amount <= source.balance
    modifies source, destination
    ensures source.balance == old(source.balance) - amount
    ensures destination.balance == old(destination.balance) + amount
    ensures source.balance >= 0
    ensures destination.balance >= 0
    ensures source.balance + destination.balance == old(source.balance) + old(destination.balance)
  {
    source.balance := source.balance - amount;
    destination.balance := destination.balance + amount;
  }
}
