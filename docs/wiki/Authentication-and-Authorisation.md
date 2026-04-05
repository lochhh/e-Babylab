Essentially, authentication verifies the identity of a user and authorisation determines the operations an authenticated
user can perform on a system. Authentication and authorisation administration is only accessible by a site administrator.
Hence, a site administrator's "capabilities" include:

* adding groups (e.g., for different research labs),
* assigning group permissions,
![Add group](https://github.com/user-attachments/assets/fa89c323-6e6a-47e9-9d79-c30ced1ec1f1)
* adding users,
![Add user](https://github.com/user-attachments/assets/4ec8c923-901e-4dd1-945b-0d83a912a44e)
* assigning users to groups, and
* assigning user permissions, including the permission to login to e-Babylab (i.e., staff status)
![Assign permissions](https://github.com/user-attachments/assets/652f982b-5f7b-481e-855b-d6f63beb8b50)

By default, an administrator (i.e., user with superuser status) has all permissions needed to perform particular functions within e-Babylab (e.g., adding a user, changing an experiment, assigning permissions) without explicitly assigning them. A normal user, on the other hand, does not have any permissions, but instead requires permissions to be assigned by another user who has the permission to do so (e.g., an administrator). 
> [!NOTE] 
>
> Permissions for a normal user **must exclude** everything under the _admin_ and _auth_ modules (see screenshot above). 

An experiment, including its participant data and results, can be made accessible to other users through groups. For instance, a group can be created for a particular research group or laboratory and an experiment can be shared among all users belonging to this group. As permissions can be assigned on a group-level, groups can also be used to more efficiently manage access rights by assigning users to groups. In other words, a user need not be directly assigned permissions, but rather acquire them through their assigned group(s).