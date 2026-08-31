class ProtectedAccessSystem {
  var authorizedUsers: set<string>

  constructor()
    ensures authorizedUsers == {}
  {
    authorizedUsers := {};
  }

  function IsAuthorized(user: string): bool
    reads this
  {
    user in authorizedUsers
  }

  method RequestAccess(user: string) returns (granted: bool)
    reads this
    ensures granted <==> user in authorizedUsers
    ensures ! (user in authorizedUsers) ==> !granted
  {
    granted := user in authorizedUsers;
  }

  method GrantAuthorization(user: string)
    modifies this
    ensures authorizedUsers == old(authorizedUsers) + {user}
  {
    authorizedUsers := authorizedUsers + {user};
  }

  method RevokeAuthorization(user: string)
    modifies this
    ensures authorizedUsers == old(authorizedUsers) - {user}
  {
    authorizedUsers := authorizedUsers - {user};
  }
}
