class AccessControl
{
  var authorizedUsers: set<string>

  constructor()
    ensures authorizedUsers == set {}
  {
    authorizedUsers := set {}
  }

  predicate Authorized(user: string)
    reads this
  {
    user in authorizedUsers
  }

  method GrantAuthorization(user: string)
    modifies this
    ensures Authorized(user)
    ensures authorizedUsers == old(authorizedUsers) + {user}
  {
    authorizedUsers := authorizedUsers + {user}
  }

  method RevokeAuthorization(user: string)
    modifies this
    ensures !Authorized(user)
    ensures authorizedUsers == old(authorizedUsers) - {user}
  {
    authorizedUsers := authorizedUsers - {user}
  }

  method RequestProtectedResource(user: string) returns (accessGranted: bool)
    ensures accessGranted <==> user in old(authorizedUsers)
    ensures accessGranted ==> Authorized(user)
    ensures !Authorized(user) ==> !accessGranted
    ensures authorizedUsers == old(authorizedUsers)
  {
    accessGranted := Authorized(user)
  }
}
