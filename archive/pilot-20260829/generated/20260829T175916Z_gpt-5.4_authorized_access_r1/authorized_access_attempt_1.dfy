module AuthorizedAccessSystem {
  type User = int

  class AccessController {
    var authorizedUsers: set<User>

    constructor ()
      ensures authorizedUsers == {}
    {
      authorizedUsers := {};
    }

    method GrantAuthorization(user: User)
      modifies this
      ensures authorizedUsers == old(authorizedUsers) + {user}
    {
      authorizedUsers := authorizedUsers + {user};
    }

    method RevokeAuthorization(user: User)
      modifies this
      ensures authorizedUsers == old(authorizedUsers) - {user}
    {
      authorizedUsers := authorizedUsers - {user};
    }

    method RequestAccess(user: User) returns (accessGranted: bool)
      ensures accessGranted <==> user in authorizedUsers
      ensures authorizedUsers == old(authorizedUsers)
    {
      accessGranted := user in authorizedUsers;
    }
  }
}
